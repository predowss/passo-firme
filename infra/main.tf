locals {
  nome = var.projeto

  tags = merge({
    projeto        = "passo-firme"
    disciplina     = "secure-devops-cloud"
    evento         = "fiap-gs-2026-2"
    gerenciado_por = "terraform"
  }, var.tags)
}

data "azurerm_client_config" "atual" {}

# Sufixo para nomes que precisam ser únicos no mundo (ACR e Postgres).
resource "random_string" "sufixo" {
  length  = 5
  upper   = false
  special = false
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.nome}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.nome}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  # Teto de ingestão diária: protege os créditos de um log descontrolado.
  daily_quota_gb = 1
  tags           = local.tags
}
