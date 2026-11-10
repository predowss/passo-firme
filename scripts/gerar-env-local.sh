#!/usr/bin/env bash
# Cria o .env local com valores aleatórios (nenhuma senha é digitada nem versionada).
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  echo ".env já existe; nada a fazer."
  exit 0
fi

umask 077
cat > .env <<ENV
POSTGRES_PASSWORD=$(openssl rand -hex 16)
GRAFANA_ADMIN_PASSWORD=$(openssl rand -hex 12)
METRICS_TOKEN=
OPS_TOKEN=$(openssl rand -hex 16)
AUTOR_SALT=$(openssl rand -hex 24)
CORS_ORIGINS=http://localhost:5173
ENV
echo ".env criado (permissão 600). Senha do Grafana: grep GRAFANA_ADMIN_PASSWORD .env"
