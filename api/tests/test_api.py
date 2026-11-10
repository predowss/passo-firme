"""Testes da API v0. Rodam no pipeline (job "testes") com SQLite temporário."""

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import create_app

PNG_FALSO = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 4
# Valores de teste gerados em tempo de execução: nada com cara de segredo no repositório.
TOKEN_METRICAS = "m" * 16
TOKEN_OPS = "o" * 16


def _config(tmp_path, **extra) -> Config:
    valores = {
        "ambiente": "teste",
        "versao": "teste",
        "database_url": f"sqlite:///{tmp_path / 'teste.db'}",
        "metrics_token": TOKEN_METRICAS,
        "ops_token": TOKEN_OPS,
        "autor_salt": "s" * 16,
        "cors_origins": [],
        "limite_req_por_minuto": 1000,
        "tamanho_max_foto_mb": 1,
    }
    valores.update(extra)
    return Config(**valores)


@pytest.fixture
def cliente(tmp_path):
    with TestClient(create_app(_config(tmp_path))) as c:
        yield c


def _criar_relato(cliente, **campos):
    dados = {"lat": "-23.5505199", "lon": "-46.6333094", "distrito": "Itaquera", **campos}
    arquivos = {"foto": ("calcada.png", PNG_FALSO, "image/png")}
    return cliente.post("/relatos", data=dados, files=arquivos)


def test_health_ok(cliente):
    resposta = cliente.get("/health")
    assert resposta.status_code == 200
    assert resposta.json()["banco"] == "ok"


def test_cria_relato_com_deteccao_e_coordenada_arredondada(cliente):
    resposta = _criar_relato(cliente, autor_id="cidadao-123")
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "recebido"
    assert corpo["lat"] == -23.5505
    assert corpo["deteccoes"], "a foto deveria gerar ao menos uma detecção simulada"
    assert "autor_hash" not in corpo and "autor_id" not in corpo

    lista = cliente.get("/relatos", params={"distrito": "Itaquera"}).json()
    assert [r["id"] for r in lista] == [corpo["id"]]


def test_rejeita_foto_de_tipo_invalido(cliente):
    resposta = cliente.post(
        "/relatos",
        data={"lat": "-23.5", "lon": "-46.6"},
        files={"foto": ("nota.txt", b"texto", "text/plain")},
    )
    assert resposta.status_code == 415


def test_rejeita_foto_grande(cliente):
    grande = b"\x00" * (1024 * 1024 + 1)
    resposta = cliente.post(
        "/relatos",
        data={"lat": "-23.5", "lon": "-46.6"},
        files={"foto": ("grande.png", grande, "image/png")},
    )
    assert resposta.status_code == 413


def test_transicoes_de_status(cliente):
    relato_id = _criar_relato(cliente).json()["id"]
    url = f"/relatos/{relato_id}/status"

    assert cliente.patch(url, json={"status": "resolvido"}).status_code == 409
    assert cliente.patch(url, json={"status": "em_triagem", "prioridade": 4}).status_code == 200
    encaminhado = cliente.patch(
        url,
        json={"status": "encaminhado", "responsavel": "proprietario", "base_legal": "Lei 15.442/2011"},
    )
    assert encaminhado.status_code == 200
    assert encaminhado.json()["prioridade"] == 4
    assert cliente.patch(url, json={"status": "resolvido"}).status_code == 200
    assert cliente.patch("/relatos/9999/status", json={"status": "em_triagem"}).status_code == 404


def test_metrics_exige_token(cliente):
    cliente.get("/indicadores")
    assert cliente.get("/metrics").status_code == 401
    resposta = cliente.get("/metrics", headers={"Authorization": f"Bearer {TOKEN_METRICAS}"})
    assert resposta.status_code == 200
    assert 'http_requests_total{method="GET",rota="/indicadores",status="200"}' in resposta.text
    assert "process_resident_memory_bytes" in resposta.text


def test_rota_de_falha_simulada_fica_escondida_sem_token(cliente):
    assert cliente.get("/ops/simular-erro").status_code == 404
    assert cliente.get("/ops/simular-erro", headers={"X-Ops-Token": "errado"}).status_code == 404
    assert cliente.get("/ops/simular-erro", headers={"X-Ops-Token": TOKEN_OPS}).status_code == 500


def test_assistente_responde_com_fonte_ou_recusa(cliente):
    com_fonte = cliente.post("/assistente", json={"pergunta": "Quem conserta a calçada?"}).json()
    assert com_fonte["recusa"] is False and com_fonte["fontes"]
    recusa = cliente.post("/assistente", json={"pergunta": "Qual a previsão do tempo?"}).json()
    assert recusa["recusa"] is True and recusa["fontes"] == []


def test_robo_aceita_uma_leitura_ou_lote(cliente):
    leitura = {"robo_id": "robo-1", "lat": -23.54, "lon": -46.47, "faixa_livre_cm": 95, "piso": "irregular"}
    assert cliente.post("/robo/leituras", json=leitura).json() == {"gravadas": 1}
    assert cliente.post("/robo/leituras", json=[leitura, leitura]).json() == {"gravadas": 2}
    assert cliente.get("/indicadores").json()["leituras_robo"] == 3


def test_indicadores(cliente):
    _criar_relato(cliente)
    corpo = cliente.get("/indicadores").json()
    assert corpo["relatos"] == 1
    assert corpo["por_status"] == {"recebido": 1}


def test_limite_de_requisicoes(tmp_path):
    with TestClient(create_app(_config(tmp_path, limite_req_por_minuto=3))) as c:
        codigos = [c.get("/").status_code for _ in range(4)]
        assert codigos == [200, 200, 200, 429]
        assert c.get("/health").status_code == 200  # rotas internas ficam fora do limite
