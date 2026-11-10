"""API v0 do Passo Firme: o ponto onde todas as disciplinas se conectam.

Contrato v0 (seção "Arquitetura" do plano do grupo):
    POST  /relatos                 app            foto + GPS -> detecção -> relato
    GET   /relatos                 app, painel, RPA
    PATCH /relatos/{id}/status     RPA            triagem, prioridade, encaminhamento
    POST  /detectar                API            detector (simulado até a Visão plugar o YOLO)
    POST  /assistente              app, RPA       assistente (simulado até a IA plugar a LLM)
    POST  /robo/leituras           robô           leituras do Maker Lab
    GET   /indicadores             painel         números para o painel e o pitch
Operação:
    GET   /health                  probes e teste de fumaça do pipeline
    GET   /metrics                 Prometheus (Bearer token em produção)
    GET   /ops/simular-erro        dispara o alerta de 5xx de propósito (com token)
"""

import hashlib
import hmac
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import servicos
from .config import Config
from .db import BancoDeDados, Deteccao, Encaminhamento, LeituraRobo, Relato, agora
from .observabilidade import Metricas, endpoint_metricas, instalar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("passo_firme.api")

Status = Literal["recebido", "em_triagem", "revisao_humana", "encaminhado", "resolvido", "descartado"]
TRANSICOES: dict[str, set[str]] = {
    "recebido": {"em_triagem", "revisao_humana", "descartado"},
    "em_triagem": {"encaminhado", "revisao_humana", "descartado"},
    "revisao_humana": {"em_triagem", "encaminhado", "descartado"},
    "encaminhado": {"resolvido"},
    "resolvido": set(),
    "descartado": set(),
}
TIPOS_DE_FOTO = {"image/jpeg", "image/png", "image/webp"}
CASAS_DECIMAIS_GPS = 4  # cerca de 11 metros: localiza a barreira sem expor a casa de ninguém


# ---------- Esquemas ----------


class DeteccaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    classe: str
    confianca: float
    caixa: list[float]


class RelatoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    criado_em: datetime
    lat: float
    lon: float
    distrito: str | None
    descricao: str | None
    status: str
    prioridade: int | None
    deteccoes: list[DeteccaoOut]


class MudancaStatus(BaseModel):
    status: Status
    prioridade: int | None = Field(default=None, ge=1, le=5)
    responsavel: Literal["proprietario", "prefeitura", "concessionaria"] | None = None
    base_legal: str | None = Field(default=None, max_length=200)


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500)


class Fonte(BaseModel):
    titulo: str
    trecho: str


class RespostaAssistente(BaseModel):
    resposta: str
    fontes: list[Fonte]
    recusa: bool
    modelo: str


class LeituraIn(BaseModel):
    robo_id: str = Field(min_length=1, max_length=40)
    momento: datetime | None = None
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    faixa_livre_cm: float | None = Field(default=None, ge=0, le=1000)
    trepidacao: float | None = Field(default=None, ge=0)
    inclinacao_pct: float | None = Field(default=None, ge=-100, le=100)
    piso: Literal["liso", "irregular", "degrau", "buraco", "desconhecido"] = "desconhecido"


# ---------- Aplicação ----------


def create_app(config: Config | None = None) -> FastAPI:
    config = config or Config()
    banco = BancoDeDados(config.database_url)
    metricas = Metricas()

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI):
        banco.criar_tabelas()
        log.info("API pronta: ambiente=%s versao=%s", config.ambiente, config.versao)
        yield
        banco.engine.dispose()

    app = FastAPI(
        title="Passo Firme API",
        version="0.1.0",
        description="Mapeia, prioriza e encaminha barreiras nas calçadas de São Paulo.",
        lifespan=ciclo_de_vida,
    )

    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_methods=["GET", "POST", "PATCH"],
            allow_headers=["Content-Type", "Authorization"],
        )
    instalar(app, metricas, config.limite_req_por_minuto, config.producao)
    app.add_api_route("/metrics", endpoint_metricas(metricas, config.metrics_token), include_in_schema=False)

    SessaoDep = Annotated[Session, Depends(banco.sessao)]
    limite_foto = config.tamanho_max_foto_mb * 1024 * 1024

    def hash_autor(autor_id: str | None) -> str | None:
        if not autor_id:
            return None
        return hmac.new(config.autor_salt.encode(), autor_id.encode(), hashlib.sha256).hexdigest()

    async def ler_foto(foto: UploadFile | None) -> bytes:
        if foto is None:
            return b""
        if foto.content_type not in TIPOS_DE_FOTO:
            raise HTTPException(415, "Envie a foto em JPEG, PNG ou WebP.")
        conteudo = await foto.read(limite_foto + 1)
        if len(conteudo) > limite_foto:
            raise HTTPException(413, f"A foto passa de {config.tamanho_max_foto_mb} MB.")
        return conteudo

    # ----- Operação -----

    @app.get("/", tags=["operacao"])
    def raiz():
        return {
            "nome": "Passo Firme API",
            "versao": config.versao,
            "ambiente": config.ambiente,
            "documentacao": "/docs",
            "saude": "/health",
        }

    @app.get("/health", tags=["operacao"])
    def saude():
        if banco.saudavel():
            return {"status": "ok", "banco": "ok", "versao": config.versao}
        return JSONResponse(
            {"status": "degradado", "banco": "indisponivel", "versao": config.versao},
            status_code=503,
        )

    @app.get("/ops/simular-erro", include_in_schema=False)
    def simular_erro(x_ops_token: Annotated[str | None, Header()] = None):
        # Sem token configurado, ou com token errado, a rota "não existe".
        if not config.ops_token or not x_ops_token or not hmac.compare_digest(x_ops_token, config.ops_token):
            raise HTTPException(404)
        log.warning("falha simulada solicitada para testar o alerta de 5xx")
        return JSONResponse({"erro": "falha simulada para teste de alerta"}, status_code=500)

    # ----- Relatos -----

    @app.post("/relatos", response_model=RelatoOut, status_code=201, tags=["relatos"])
    async def criar_relato(
        sessao: SessaoDep,
        lat: Annotated[float, Form(ge=-90, le=90)],
        lon: Annotated[float, Form(ge=-180, le=180)],
        descricao: Annotated[str | None, Form(max_length=500)] = None,
        distrito: Annotated[str | None, Form(max_length=80)] = None,
        autor_id: Annotated[str | None, Form(max_length=128)] = None,
        foto: Annotated[UploadFile | None, File()] = None,
    ):
        imagem = await ler_foto(foto)
        relato = Relato(
            lat=round(lat, CASAS_DECIMAIS_GPS),
            lon=round(lon, CASAS_DECIMAIS_GPS),
            descricao=descricao,
            distrito=distrito,
            autor_hash=hash_autor(autor_id),
            foto_url=None,  # a foto só será guardada depois do borramento (Visão, 14/11)
        )
        for item in servicos.detectar_barreiras(imagem):
            relato.deteccoes.append(Deteccao(**item))
        sessao.add(relato)
        sessao.commit()
        metricas.relatos.inc()
        return relato

    @app.get("/relatos", response_model=list[RelatoOut], tags=["relatos"])
    def listar_relatos(
        sessao: SessaoDep,
        status: Status | None = None,
        distrito: Annotated[str | None, Query(max_length=80)] = None,
        limite: Annotated[int, Query(ge=1, le=200)] = 50,
    ):
        consulta = select(Relato).order_by(Relato.criado_em.desc()).limit(limite)
        if status:
            consulta = consulta.where(Relato.status == status)
        if distrito:
            consulta = consulta.where(Relato.distrito == distrito)
        return sessao.scalars(consulta).all()

    @app.patch("/relatos/{relato_id}/status", response_model=RelatoOut, tags=["relatos"])
    def mudar_status(relato_id: int, mudanca: MudancaStatus, sessao: SessaoDep):
        relato = sessao.get(Relato, relato_id)
        if relato is None:
            raise HTTPException(404, "Relato não encontrado.")
        if mudanca.status != relato.status and mudanca.status not in TRANSICOES[relato.status]:
            raise HTTPException(409, f"Não dá para ir de '{relato.status}' para '{mudanca.status}'.")
        relato.status = mudanca.status
        if mudanca.prioridade is not None:
            relato.prioridade = mudanca.prioridade
        if mudanca.status == "encaminhado" and mudanca.responsavel:
            relato.encaminhamentos.append(
                Encaminhamento(
                    responsavel=mudanca.responsavel,
                    base_legal=mudanca.base_legal,
                    protocolo_simulado=f"SIM-{relato.id}-{agora():%Y%m%d%H%M}",
                )
            )
        sessao.commit()
        return relato

    # ----- Peças das outras trilhas -----

    @app.post("/detectar", tags=["visao"])
    async def detectar(foto: Annotated[UploadFile, File()]):
        imagem = await ler_foto(foto)
        return {"modelo": servicos.MODELO_SIMULADO, "deteccoes": servicos.detectar_barreiras(imagem)}

    @app.post("/assistente", response_model=RespostaAssistente, tags=["ia"])
    def assistente(pergunta: Pergunta):
        return servicos.responder_pergunta(pergunta.pergunta)

    @app.post("/robo/leituras", status_code=201, tags=["robo"])
    def gravar_leituras(leituras: LeituraIn | list[LeituraIn], sessao: SessaoDep):
        # Aceita uma leitura ou um lote (o robô guarda o que não conseguiu enviar sem rede).
        lote = leituras if isinstance(leituras, list) else [leituras]
        if not 1 <= len(lote) <= 500:
            raise HTTPException(422, "Envie de 1 a 500 leituras por vez.")
        for leitura in lote:
            dados = leitura.model_dump()
            dados["momento"] = dados["momento"] or agora()
            dados["lat"] = round(dados["lat"], CASAS_DECIMAIS_GPS)
            dados["lon"] = round(dados["lon"], CASAS_DECIMAIS_GPS)
            sessao.add(LeituraRobo(**dados))
        sessao.commit()
        return {"gravadas": len(lote)}

    @app.get("/indicadores", tags=["painel"])
    def indicadores(sessao: SessaoDep):
        por_status = dict(sessao.execute(select(Relato.status, func.count()).group_by(Relato.status)).all())
        total = sum(por_status.values())
        resolvidos = por_status.get("resolvido", 0)
        return {
            "relatos": total,
            "por_status": por_status,
            "resolvidos_pct": round(100 * resolvidos / total, 1) if total else 0.0,
            "barreiras_detectadas": sessao.scalar(select(func.count()).select_from(Deteccao)) or 0,
            "leituras_robo": sessao.scalar(select(func.count()).select_from(LeituraRobo)) or 0,
            "fonte": "banco operacional da API (a camada Ouro do Big Data entra no lugar)",
        }

    return app


app = create_app()
