# syntax=docker/dockerfile:1
# Imagem enxuta da API do Passo Firme.
# - multi-stage: compiladores e cache do pip ficam no estágio de build
# - base slim, sem ferramentas extras
# - usuário sem privilégio (UID 10001) e código somente leitura
# - nenhum segredo: tudo chega por variável de ambiente em tempo de execução

FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
# O pip sai do venv no fim: a imagem final não precisa instalar nada.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt \
    && /opt/venv/bin/pip uninstall --yes pip

FROM python:3.12-slim AS runtime
# Versão (SHA do commit) gravada na imagem pelo pipeline; aparece em /health.
ARG APP_VERSION=dev
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_VERSION=${APP_VERSION}
# Correção de segurança: o Trivy barrou o zlib1g da imagem base (CVE-2026-85091,
# heap overflow), já corrigido pelo Debian em 1.3.1-1+deb13u1. Atualiza só esse
# pacote; remover quando a python:3.12-slim já vier com a versão corrigida.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends --only-upgrade zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
WORKDIR /srv
COPY --from=build /opt/venv /opt/venv
# Arquivos pertencem ao root: o processo (UID 10001) lê, mas não altera o código.
COPY app ./app
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).status == 200 else 1)"]
# --no-access-log: o log de acesso do uvicorn grava o IP do cidadão; o da API não grava.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log", "--no-server-header"]
