"""Configuração da API, lida só de variáveis de ambiente.

Nada de segredo no código nem na imagem: em produção os valores chegam pelos
"secrets" do Azure Container Apps (criados pelo Terraform); localmente, pelo .env
do docker compose.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field


def _lista(valor: str | None) -> list[str]:
    return [item.strip() for item in (valor or "").split(",") if item.strip()]


def _salt_padrao() -> str:
    # Sem AUTOR_SALT, cada processo gera o seu: serve para desenvolvimento,
    # mas em produção o hash do autor precisa ser estável, então o Terraform
    # sempre define a variável.
    return os.getenv("AUTOR_SALT") or secrets.token_hex(24)


@dataclass(frozen=True)
class Config:
    ambiente: str = field(default_factory=lambda: os.getenv("APP_ENV", "local"))
    versao: str = field(default_factory=lambda: os.getenv("APP_VERSION", "dev"))
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./passo-firme.db")
    )
    # Token exigido em /metrics (Bearer). Vazio = endpoint aberto (só para uso local).
    metrics_token: str = field(default_factory=lambda: os.getenv("METRICS_TOKEN", ""))
    # Token da rota de teste de alerta. Vazio = rota desligada (responde 404).
    ops_token: str = field(default_factory=lambda: os.getenv("OPS_TOKEN", ""))
    autor_salt: str = field(default_factory=_salt_padrao)
    cors_origins: list[str] = field(default_factory=lambda: _lista(os.getenv("CORS_ORIGINS")))
    limite_req_por_minuto: int = field(
        default_factory=lambda: int(os.getenv("LIMITE_REQ_POR_MINUTO", "120"))
    )
    tamanho_max_foto_mb: int = field(
        default_factory=lambda: int(os.getenv("TAMANHO_MAX_FOTO_MB", "5"))
    )

    @property
    def producao(self) -> bool:
        return self.ambiente == "producao"
