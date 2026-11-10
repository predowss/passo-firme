#!/usr/bin/env bash
# Prepara a assinatura Azure para o Terraform. Rodar UMA vez, por um integrante.
#   - registra os provedores de recurso usados
#   - mostra as regiões liberadas (Azure for Students restringe regiões)
#   - cria o Storage Account do state remoto (sem chave de acesso, só Entra ID)
#   - gera infra/backend.hcl e infra/terraform.tfvars (ambos fora do Git)
# Uso: LOCATION=eastus2 ./scripts/01-bootstrap-azure.sh
set -euo pipefail
cd "$(dirname "$0")/.."

LOCATION="${LOCATION:-eastus2}"
RG_STATE="${RG_STATE:-rg-passofirme-tfstate}"

command -v az >/dev/null || { echo "Instale a Azure CLI: https://aka.ms/azure-cli" >&2; exit 1; }
az account show >/dev/null 2>&1 || az login --output none

SUB_ID=$(az account show --query id --output tsv)
echo "Assinatura: $(az account show --query name --output tsv) (${SUB_ID})"
echo "Região: ${LOCATION}"

echo "==> Registrando provedores de recurso"
for ns in Microsoft.App Microsoft.ContainerRegistry Microsoft.DBforPostgreSQL \
          Microsoft.ManagedIdentity Microsoft.Network Microsoft.OperationalInsights \
          Microsoft.Insights Microsoft.Storage Microsoft.Consumption; do
  az provider register --namespace "$ns" --output none
done

echo "==> Políticas da assinatura (procure 'Allowed resource deployment regions')"
az policy assignment list \
  --query "[].{politica:displayName, regioes:parameters.listOfAllowedLocations.value}" \
  --output jsonc || true

echo "==> PostgreSQL Flexible Server disponível em ${LOCATION}?"
if ! az postgres flexible-server list-skus --location "$LOCATION" --query "[0].name" --output tsv >/dev/null 2>&1; then
  echo "AVISO: não consegui listar SKUs de Postgres em ${LOCATION}. Se o apply falhar, troque a região." >&2
fi

if [[ -f infra/backend.hcl ]]; then
  echo "==> infra/backend.hcl já existe; mantendo o state atual."
else
  SA="stpftfstate$(openssl rand -hex 3)"
  echo "==> Criando o state remoto: ${RG_STATE}/${SA}"
  az group create --name "$RG_STATE" --location "$LOCATION" \
    --tags projeto=passo-firme finalidade=terraform-state --output none
  az storage account create --name "$SA" --resource-group "$RG_STATE" --location "$LOCATION" \
    --sku Standard_LRS --kind StorageV2 --https-only true --min-tls-version TLS1_2 \
    --allow-blob-public-access false --allow-shared-key-access false --output none
  az storage account blob-service-properties update --account-name "$SA" --resource-group "$RG_STATE" \
    --enable-versioning true --enable-delete-retention true --delete-retention-days 7 --output none

  SA_ID=$(az storage account show --name "$SA" --resource-group "$RG_STATE" --query id --output tsv)
  USER_ID=$(az ad signed-in-user show --query id --output tsv)
  az role assignment create --assignee-object-id "$USER_ID" --assignee-principal-type User \
    --role "Storage Blob Data Contributor" --scope "$SA_ID" --output none

  echo "    aguardando a permissão propagar..."
  for _ in $(seq 1 18); do
    if az storage container create --name tfstate --account-name "$SA" --auth-mode login --output none 2>/dev/null; then
      break
    fi
    sleep 10
  done

  cat > infra/backend.hcl <<HCL
resource_group_name  = "${RG_STATE}"
storage_account_name = "${SA}"
container_name       = "tfstate"
key                  = "passo-firme.tfstate"
use_azuread_auth     = true
HCL
  echo "    infra/backend.hcl criado."
  echo "    Outros integrantes que forem rodar o Terraform precisam do papel"
  echo "    'Storage Blob Data Contributor' nesse Storage Account."
fi

if [[ ! -f infra/terraform.tfvars ]]; then
  sed -e "s/00000000-0000-0000-0000-000000000000/${SUB_ID}/" \
      -e "s/\"eastus2\"/\"${LOCATION}\"/" \
      infra/terraform.tfvars.example > infra/terraform.tfvars
  echo "==> infra/terraform.tfvars criado: ajuste github_repositorio e emails_alerta."
fi

cat <<TXT

Próximos passos:
  cd infra
  terraform init -backend-config=backend.hcl
  terraform plan -out tfplan
  terraform apply tfplan
  cd .. && ./scripts/02-configurar-github.sh
TXT
