#!/usr/bin/env bash
# Aponta o Prometheus local para o MVP publicado na Azure e sobe Prometheus + Grafana.
set -euo pipefail
cd "$(dirname "$0")/.."

URL=$(terraform -chdir=infra output -raw api_url)
HOST="${URL#https://}"

mkdir -p observabilidade/alvos observabilidade/segredos
printf '[{"targets": ["%s"], "labels": {"ambiente": "azure"}}]\n' "$HOST" > observabilidade/alvos/azure.json
terraform -chdir=infra output -raw metrics_token > observabilidade/segredos/metrics_token
# O Prometheus roda como usuário "nobody" no container e precisa ler o arquivo.
# A pasta está no .gitignore e o arquivo só existe na sua máquina.
chmod 644 observabilidade/segredos/metrics_token

[[ -f .env ]] || ./scripts/gerar-env-local.sh
docker compose --profile obs up -d

echo "Prometheus: http://localhost:9090/targets  (job api-azure deve ficar UP)"
echo "Grafana:    http://localhost:3000  (usuário admin; senha no .env)"
