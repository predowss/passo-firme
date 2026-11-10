# Azure Container Apps: containers serverless, HTTPS gerenciado e escala a zero.

resource "azurerm_container_app_environment" "main" {
  name                               = "cae-${local.nome}"
  location                           = azurerm_resource_group.main.location
  resource_group_name                = azurerm_resource_group.main.name
  logs_destination                   = "log-analytics"
  log_analytics_workspace_id         = azurerm_log_analytics_workspace.main.id
  infrastructure_subnet_id           = azurerm_subnet.apps.id
  infrastructure_resource_group_name = "ME_rg-${local.nome}"
  internal_load_balancer_enabled     = false
  tags                               = local.tags

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

resource "random_password" "metrics_token" {
  length  = 40
  special = false
}

resource "random_password" "ops_token" {
  length  = 40
  special = false
}

resource "random_password" "autor_salt" {
  length  = 48
  special = false
}

resource "azurerm_container_app" "api" {
  name                         = "ca-${local.nome}-api"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.api.id
  }

  # Segredos guardados criptografados no Container App; o código só vê variáveis de ambiente.
  secret {
    name  = "database-url"
    value = local.database_url
  }

  secret {
    name  = "metrics-token"
    value = random_password.metrics_token.result
  }

  secret {
    name  = "ops-token"
    value = random_password.ops_token.result
  }

  secret {
    name  = "autor-salt"
    value = random_password.autor_salt.result
  }

  ingress {
    external_enabled           = true
    target_port                = 8080
    transport                  = "auto"
    allow_insecure_connections = false

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.api_min_replicas
    max_replicas = var.api_max_replicas

    container {
      name   = "api"
      image  = var.imagem_inicial
      cpu    = var.api_cpu
      memory = var.api_memoria

      env {
        name  = "APP_ENV"
        value = "producao"
      }

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }

      env {
        name        = "METRICS_TOKEN"
        secret_name = "metrics-token"
      }

      env {
        name        = "OPS_TOKEN"
        secret_name = "ops-token"
      }

      env {
        name        = "AUTOR_SALT"
        secret_name = "autor-salt"
      }

      env {
        name  = "CORS_ORIGINS"
        value = var.cors_origins
      }

      env {
        name  = "LIMITE_REQ_POR_MINUTO"
        value = tostring(var.limite_req_por_minuto)
      }
    }
  }

  lifecycle {
    # Quem troca a imagem é o pipeline a cada deploy, não o Terraform.
    ignore_changes = [template[0].container[0].image]
  }

  depends_on = [azurerm_role_assignment.api_acr_pull]
}
