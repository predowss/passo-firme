terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # State remoto num Storage Account (criado por scripts/01-bootstrap-azure.sh),
  # com autenticação pelo Entra ID e sem chave de acesso. Os valores ficam no
  # backend.hcl, que não vai para o Git:
  #   terraform init -backend-config=backend.hcl
  backend "azurerm" {}
}

provider "azurerm" {
  subscription_id = var.subscription_id

  features {
    resource_group {
      # Ambiente acadêmico: permite o "terraform destroy" no fim da correção
      # mesmo que a Azure tenha criado recursos auxiliares no grupo.
      prevent_deletion_if_contains_resources = false
    }
  }
}
