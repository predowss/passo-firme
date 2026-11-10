#!/usr/bin/env bash
# Gera erros 5xx de propósito para disparar os alertas (evidência para o PDF).
# Uso: ./scripts/disparar-alerta.sh            -> MVP na Azure (alerta por e-mail)
#      ./scripts/disparar-alerta.sh --local    -> API do docker compose
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--local" ]]; then
  URL="http://localhost:8080"
  TOKEN=$(grep '^OPS_TOKEN=' .env | cut -d= -f2-)
else
  URL=$(terraform -chdir=infra output -raw api_url)
  TOKEN=$(terraform -chdir=infra output -raw ops_token)
fi
TOTAL="${TOTAL:-40}"

echo "Enviando ${TOTAL} requisições que respondem 500 para ${URL} ..."
for i in $(seq 1 "$TOTAL"); do
  codigo=$(curl -s -o /dev/null -w '%{http_code}' -H "X-Ops-Token: ${TOKEN}" "${URL}/ops/simular-erro")
  echo "  ${i}/${TOTAL} -> HTTP ${codigo}"
  sleep 3
done
cat <<TXT

Agora, em 1 a 5 minutos:
  - Azure Monitor: alerta "alerta-passofirme-api-erros-5xx" disparado + e-mail
    (Portal > Monitor > Alertas)
  - Prometheus: alerta APIErros5xx em FIRING (http://localhost:9090/alerts)
  - Grafana: painel "Alertas disparando" e o gráfico de erros
Tire os prints com data e hora visíveis.
TXT
