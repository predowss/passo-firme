"""Métricas Prometheus das 4 métricas de ouro, log de acesso sem dado pessoal,
limite de requisições e cabeçalhos de segurança.

- Latência:  http_request_duration_seconds (histograma, por rota)
- Tráfego:   http_requests_total (contador, por rota e status)
- Erros:     http_requests_total{status=~"5.."}
- Saturação: http_requests_in_progress + process_cpu_seconds_total
             + process_resident_memory_bytes (coletores padrão do processo)
"""

import hmac
import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from prometheus_client import gc_collector, platform_collector, process_collector
from starlette.routing import Match

log_acesso = logging.getLogger("passo_firme.acesso")

# Rotas fora das métricas e do limite: não são tráfego de usuário.
ROTAS_INTERNAS = {"/metrics", "/health"}


class Metricas:
    """Registro próprio por aplicação (permite várias instâncias nos testes)."""

    def __init__(self) -> None:
        self.registro = CollectorRegistry()
        process_collector.ProcessCollector(registry=self.registro)
        platform_collector.PlatformCollector(registry=self.registro)
        gc_collector.GCCollector(registry=self.registro)

        self.requisicoes = Counter(
            "http_requests_total",
            "Requisições HTTP atendidas",
            ["method", "rota", "status"],
            registry=self.registro,
        )
        self.duracao = Histogram(
            "http_request_duration_seconds",
            "Tempo de resposta das requisições HTTP",
            ["method", "rota"],
            buckets=(0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registro,
        )
        self.em_andamento = Gauge(
            "http_requests_in_progress",
            "Requisições HTTP sendo processadas agora",
            registry=self.registro,
        )
        self.relatos = Counter(
            "passo_firme_relatos_total",
            "Relatos de barreira recebidos pela API",
            registry=self.registro,
        )

    def exportar(self) -> bytes:
        return generate_latest(self.registro)


def _rota_modelo(app: FastAPI, request: Request) -> str:
    """Usa o caminho-modelo da rota (/relatos/{relato_id}), nunca o caminho real,
    para não explodir a cardinalidade nem vazar identificadores nas métricas."""
    rota = request.scope.get("route")
    if rota is not None and getattr(rota, "path", None):
        return rota.path
    for candidata in app.router.routes:
        correspondencia, _ = candidata.matches(request.scope)
        if correspondencia == Match.FULL:
            return getattr(candidata, "path", "desconhecida")
    return "nao_encontrada"


def instalar(app: FastAPI, metricas: Metricas, limite_por_minuto: int, producao: bool) -> None:
    janelas: dict[str, tuple[int, int]] = {}

    @app.middleware("http")
    async def medir(request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        caminho = request.url.path
        interna = caminho in ROTAS_INTERNAS

        # Limite simples por IP em janela de 1 minuto. Funciona porque o MVP roda
        # com 1 réplica; com mais réplicas, o limite passa para o ingress/API gateway.
        bloqueada = False
        if not interna and limite_por_minuto > 0:
            ip = request.client.host if request.client else "desconhecido"
            janela = int(time.time() // 60)
            janela_ip, contagem = janelas.get(ip, (janela, 0))
            contagem = contagem + 1 if janela_ip == janela else 1
            janelas[ip] = (janela, contagem)
            if len(janelas) > 10_000:
                janelas.clear()
            bloqueada = contagem > limite_por_minuto

        inicio = time.perf_counter()
        status = 500
        if not interna:
            metricas.em_andamento.inc()
        try:
            if bloqueada:
                resposta = JSONResponse(
                    {"detail": "Muitas requisições. Tente de novo em 1 minuto."},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
            else:
                resposta = await call_next(request)
            status = resposta.status_code
        finally:
            duracao = time.perf_counter() - inicio
            if not interna:
                metricas.em_andamento.dec()
                rota = _rota_modelo(app, request)
                metricas.requisicoes.labels(request.method, rota, str(status)).inc()
                metricas.duracao.labels(request.method, rota).observe(duracao)
                # Log de acesso sem IP, sem query string e sem corpo (LGPD).
                log_acesso.info(
                    "method=%s rota=%s status=%s duracao_ms=%.1f",
                    request.method,
                    rota,
                    status,
                    duracao * 1000,
                )

        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        if producao:
            resposta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return resposta


def endpoint_metricas(metricas: Metricas, token: str) -> Callable[[Request], Response]:
    def metrics(request: Request) -> Response:
        if token:
            recebido = request.headers.get("authorization", "")
            esperado = f"Bearer {token}"
            if not hmac.compare_digest(recebido.encode(), esperado.encode()):
                return Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})
        return Response(metricas.exportar(), media_type=CONTENT_TYPE_LATEST)

    return metrics
