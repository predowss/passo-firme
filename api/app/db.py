"""Modelo de dados v0 do Passo Firme (contrato fechado com as outras trilhas).

Tabelas: relato, deteccao, encaminhamento, leitura_robo e log_rpa.
Privacidade por padrão: coordenadas arredondadas, autor só como hash e
nenhuma foto guardada enquanto o borramento de rostos e placas não estiver no ar.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Engine, ForeignKey, String, create_engine, text
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

log = logging.getLogger("passo_firme.db")


def agora() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Relato(Base):
    __tablename__ = "relato"

    id: Mapped[int] = mapped_column(primary_key=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora, index=True)
    lat: Mapped[float]
    lon: Mapped[float]
    foto_url: Mapped[str | None] = mapped_column(String(500))
    autor_hash: Mapped[str | None] = mapped_column(String(64))
    distrito: Mapped[str | None] = mapped_column(String(80), index=True)
    descricao: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="recebido", index=True)
    prioridade: Mapped[int | None]

    deteccoes: Mapped[list[Deteccao]] = relationship(
        back_populates="relato", cascade="all, delete-orphan", lazy="selectin"
    )
    encaminhamentos: Mapped[list[Encaminhamento]] = relationship(
        back_populates="relato", cascade="all, delete-orphan", lazy="selectin"
    )


class Deteccao(Base):
    __tablename__ = "deteccao"

    id: Mapped[int] = mapped_column(primary_key=True)
    relato_id: Mapped[int] = mapped_column(ForeignKey("relato.id", ondelete="CASCADE"), index=True)
    classe: Mapped[str] = mapped_column(String(40))
    confianca: Mapped[float]
    caixa: Mapped[list[float]] = mapped_column(JSON)

    relato: Mapped[Relato] = relationship(back_populates="deteccoes")


class Encaminhamento(Base):
    __tablename__ = "encaminhamento"

    id: Mapped[int] = mapped_column(primary_key=True)
    relato_id: Mapped[int] = mapped_column(ForeignKey("relato.id", ondelete="CASCADE"), index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    # proprietario, prefeitura ou concessionaria
    responsavel: Mapped[str] = mapped_column(String(20))
    base_legal: Mapped[str | None] = mapped_column(String(200))
    protocolo_simulado: Mapped[str] = mapped_column(String(40))

    relato: Mapped[Relato] = relationship(back_populates="encaminhamentos")


class LeituraRobo(Base):
    __tablename__ = "leitura_robo"

    id: Mapped[int] = mapped_column(primary_key=True)
    robo_id: Mapped[str] = mapped_column(String(40), index=True)
    momento: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    lat: Mapped[float]
    lon: Mapped[float]
    faixa_livre_cm: Mapped[float | None]
    trepidacao: Mapped[float | None]
    inclinacao_pct: Mapped[float | None]
    piso: Mapped[str] = mapped_column(String(20), default="desconhecido")


class LogRpa(Base):
    __tablename__ = "log_rpa"

    id: Mapped[int] = mapped_column(primary_key=True)
    execucao_id: Mapped[str] = mapped_column(String(40), index=True)
    momento: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    itens: Mapped[int] = mapped_column(default=0)
    sucessos: Mapped[int] = mapped_column(default=0)
    falhas: Mapped[int] = mapped_column(default=0)
    mensagem: Mapped[str | None] = mapped_column(String(500))


class BancoDeDados:
    """Engine + fábrica de sessões. Uma instância por aplicação."""

    def __init__(self, url: str) -> None:
        argumentos: dict = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            argumentos["connect_args"] = {"check_same_thread": False}
        else:
            argumentos.update(pool_size=5, max_overflow=5, pool_recycle=1800)
        self.engine: Engine = create_engine(url, **argumentos)
        self.sessoes = sessionmaker(bind=self.engine, expire_on_commit=False)

    def criar_tabelas(self, tentativas: int = 10, espera_s: float = 3.0) -> None:
        # O banco pode demorar a aceitar conexões (compose subindo, Postgres
        # gerenciado acordando): tenta algumas vezes antes de desistir.
        # A evolução natural é trocar isto por migrações com Alembic.
        for tentativa in range(1, tentativas + 1):
            try:
                Base.metadata.create_all(self.engine)
                return
            except Exception as erro:  # noqa: BLE001 - registramos e tentamos de novo
                if tentativa == tentativas:
                    raise
                log.warning(
                    "banco indisponível (tentativa %s/%s): %s",
                    tentativa,
                    tentativas,
                    type(erro).__name__,
                )
                time.sleep(espera_s)

    def saudavel(self) -> bool:
        try:
            with self.engine.connect() as conexao:
                conexao.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001
            return False

    def sessao(self) -> Iterator[Session]:
        with self.sessoes() as sessao:
            yield sessao
