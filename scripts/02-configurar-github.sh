#!/usr/bin/env bash
# Depois do terraform apply: cria o environment "producao" no GitHub (deploy só a
# partir da main) e grava os identificadores do OIDC e os nomes dos recursos.
# Requer o GitHub CLI autenticado (gh auth login) com acesso de admin ao repositório.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v gh >/dev/null || { echo "Instale o GitHub CLI: https://cli.github.com" >&2; exit 1; }
gh auth status >/dev/null

saida() { terraform -chdir=infra output -raw "$1"; }

REPO=$(saida github_repositorio)
AMBIENTE=$(saida github_ambiente)
echo "==> ${REPO} | environment ${AMBIENTE}"

gh api --method PUT "repos/${REPO}/environments/${AMBIENTE}" --input - --silent <<'JSON'
{"deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
gh api --method POST "repos/${REPO}/environments/${AMBIENTE}/deployment-branch-policies" \
  -f name=main --silent 2>/dev/null || echo "    (regra da branch main já existia)"

# Identificadores usados pelo azure/login (não são senhas, mas ficam como Secrets).
gh secret set AZURE_CLIENT_ID       --repo "$REPO" --env "$AMBIENTE" --body "$(saida azure_client_id)"
gh secret set AZURE_TENANT_ID       --repo "$REPO" --env "$AMBIENTE" --body "$(saida azure_tenant_id)"
gh secret set AZURE_SUBSCRIPTION_ID --repo "$REPO" --env "$AMBIENTE" --body "$(saida azure_subscription_id)"

gh variable set ACR_NAME         --repo "$REPO" --env "$AMBIENTE" --body "$(saida acr_name)"
gh variable set ACR_LOGIN_SERVER --repo "$REPO" --env "$AMBIENTE" --body "$(saida acr_login_server)"
gh variable set RESOURCE_GROUP   --repo "$REPO" --env "$AMBIENTE" --body "$(saida resource_group)"
gh variable set CONTAINER_APP    --repo "$REPO" --env "$AMBIENTE" --body "$(saida container_app)"

echo "==> Pronto. O próximo push na main publica a API em $(saida api_url)"
