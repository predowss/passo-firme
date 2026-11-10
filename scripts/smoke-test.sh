#!/usr/bin/env bash
# Exercita o fluxo principal da API (útil para gerar tráfego antes dos prints).
# Uso: ./scripts/smoke-test.sh [URL]   (padrão: URL do Terraform)
set -euo pipefail
cd "$(dirname "$0")/.."

URL="${1:-$(terraform -chdir=infra output -raw api_url)}"
FOTO=$(mktemp)
trap 'rm -f "$FOTO"' EXIT
printf '\x89PNG\r\n\x1a\n' > "$FOTO"
head -c 2048 /dev/urandom >> "$FOTO"

echo "==> /health";      curl -fsS "${URL}/health"; echo
echo "==> POST /relatos"
curl -fsS -X POST "${URL}/relatos" \
  -F lat=-23.5431 -F lon=-46.4718 -F distrito=Itaquera \
  -F descricao="Buraco na calçada perto do ponto de ônibus" \
  -F "foto=@${FOTO};type=image/png"; echo
echo "==> GET /relatos"; curl -fsS "${URL}/relatos?limite=3"; echo
echo "==> POST /assistente"
curl -fsS -X POST "${URL}/assistente" -H 'Content-Type: application/json' \
  -d '{"pergunta":"Quem é responsável por consertar a calçada?"}'; echo
echo "==> POST /robo/leituras"
curl -fsS -X POST "${URL}/robo/leituras" -H 'Content-Type: application/json' \
  -d '{"robo_id":"robo-1","lat":-23.5431,"lon":-46.4718,"faixa_livre_cm":82,"inclinacao_pct":3.5,"piso":"irregular"}'; echo
echo "==> GET /indicadores"; curl -fsS "${URL}/indicadores"; echo
echo "OK: fluxo principal respondeu."
