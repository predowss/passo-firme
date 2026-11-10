"""Respostas simuladas das peças das outras trilhas.

O contrato (formato de entrada e saída) já é o definitivo; o conteúdo é
simulado até cada trilha plugar o serviço real:
- detectar_barreiras  -> detector YOLO (Visão Computacional)
- responder_pergunta  -> assistente com LLM local + RAG (IA Generativa)
"""

from __future__ import annotations

import hashlib

CLASSES = ("buraco", "degrau_desnivel", "obstaculo", "veiculo_na_calcada", "piso_tatil")
MODELO_SIMULADO = "simulado-v0"


def detectar_barreiras(imagem: bytes) -> list[dict]:
    """Detecção determinística a partir do hash da imagem (mesma foto, mesma resposta)."""
    if not imagem:
        return []
    resumo = hashlib.sha256(imagem).digest()
    quantidade = 1 + resumo[0] % 2
    deteccoes = []
    for indice in range(quantidade):
        base = resumo[1 + indice * 6 : 7 + indice * 6]
        x1 = round(base[1] / 255 * 0.5, 3)
        y1 = round(base[2] / 255 * 0.5, 3)
        deteccoes.append(
            {
                "classe": CLASSES[base[0] % len(CLASSES)],
                "confianca": round(0.55 + base[3] / 255 * 0.4, 2),
                "caixa": [x1, y1, round(x1 + 0.2 + base[4] / 255 * 0.3, 3), round(y1 + 0.2 + base[5] / 255 * 0.3, 3)],
            }
        )
    return deteccoes


_BASE = [
    {
        "palavras": ("calçada", "calcada", "responsável", "responsavel", "dono", "conserto", "consertar"),
        "resposta": (
            "Em São Paulo, a construção e a manutenção da calçada cabem ao proprietário ou "
            "possuidor do imóvel em frente a ela. Depois de notificado pela subprefeitura, "
            "ele tem prazo para regularizar, sob pena de multa por metro linear."
        ),
        "fontes": [
            {"titulo": "Lei Municipal 15.442/2011", "trecho": "Responsabilidade do proprietário pela calçada"},
            {"titulo": "Decreto Municipal 59.671/2020", "trecho": "Padronização e fiscalização das calçadas"},
        ],
    },
    {
        "palavras": ("acessibilidade", "deficiência", "deficiencia", "idoso", "idosa", "rampa"),
        "resposta": (
            "A Lei Brasileira de Inclusão garante à pessoa com deficiência o direito de ir e vir "
            "com segurança, o que inclui rotas acessíveis nas vias públicas."
        ),
        "fontes": [{"titulo": "Lei Federal 13.146/2015 (LBI)", "trecho": "Acessibilidade e mobilidade"}],
    },
]


def responder_pergunta(pergunta: str) -> dict:
    texto = pergunta.lower()
    for item in _BASE:
        if any(palavra in texto for palavra in item["palavras"]):
            return {"resposta": item["resposta"], "fontes": item["fontes"], "recusa": False, "modelo": MODELO_SIMULADO}
    return {
        "resposta": "Não encontrei isso na base de leis e serviços do Passo Firme.",
        "fontes": [],
        "recusa": True,
        "modelo": MODELO_SIMULADO,
    }
