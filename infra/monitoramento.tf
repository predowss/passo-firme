# Alertas do Azure Monitor sobre as métricas de plataforma do Container App,
# com aviso por e-mail. O alerta de 5xx é o que a equipe dispara de propósito
# (scripts/disparar-alerta.sh) para a evidência de "alerta disparado".

resource "azurerm_monitor_action_group" "equipe" {
  name                = "ag-${local.nome}-equipe"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "passofirme"
  tags                = local.tags

  dynamic "email_receiver" {
    for_each = { for indice, email in var.emails_alerta : tostring(indice) => email }

    content {
      name                    = "email-${email_receiver.key}"
      email_address           = email_receiver.value
      use_common_alert_schema = true
    }
  }
}

# Erros: mais de 5 respostas 5xx em 5 minutos.
resource "azurerm_monitor_metric_alert" "api_erros_5xx" {
  name                = "alerta-${local.nome}-api-erros-5xx"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_container_app.api.id]
  description         = "A API respondeu mais de 5 erros 5xx em 5 minutos."
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"
  auto_mitigate       = true
  tags                = local.tags

  criteria {
    metric_namespace       = "Microsoft.App/containerApps"
    metric_name            = "Requests"
    aggregation            = "Total"
    operator               = "GreaterThan"
    threshold              = 5
    skip_metric_validation = true

    dimension {
      name     = "statusCodeCategory"
      operator = "Include"
      values   = ["5xx"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.equipe.id
  }
}

# Latência: tempo médio de resposta acima de 2 segundos por 5 minutos.
resource "azurerm_monitor_metric_alert" "api_latencia" {
  name                = "alerta-${local.nome}-api-latencia"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_container_app.api.id]
  description         = "Tempo médio de resposta da API acima de 2 s."
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"
  auto_mitigate       = true
  tags                = local.tags

  criteria {
    metric_namespace       = "Microsoft.App/containerApps"
    metric_name            = "ResponseTime"
    aggregation            = "Average"
    operator               = "GreaterThan"
    threshold              = 2000
    skip_metric_validation = true
  }

  action {
    action_group_id = azurerm_monitor_action_group.equipe.id
  }
}

# Saturação: CPU acima de 80% do limite do container por 5 minutos.
resource "azurerm_monitor_metric_alert" "api_cpu" {
  name                = "alerta-${local.nome}-api-cpu"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_container_app.api.id]
  description         = "CPU da API acima de 80% do limite."
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"
  auto_mitigate       = true
  tags                = local.tags

  criteria {
    metric_namespace       = "Microsoft.App/containerApps"
    metric_name            = "CpuPercentage"
    aggregation            = "Average"
    operator               = "GreaterThan"
    threshold              = 80
    skip_metric_validation = true
  }

  action {
    action_group_id = azurerm_monitor_action_group.equipe.id
  }
}

# Orçamento opcional do grupo de recursos (desligado com orcamento_mensal_usd = 0).
resource "azurerm_consumption_budget_resource_group" "mensal" {
  count = var.orcamento_mensal_usd > 0 && length(var.emails_alerta) > 0 ? 1 : 0

  name              = "orcamento-${local.nome}"
  resource_group_id = azurerm_resource_group.main.id
  amount            = var.orcamento_mensal_usd
  time_grain        = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00'Z'", timestamp())
  }

  dynamic "notification" {
    for_each = [50, 80, 100]

    content {
      enabled        = true
      threshold      = notification.value
      operator       = "GreaterThanOrEqualTo"
      threshold_type = "Actual"
      contact_emails = var.emails_alerta
    }
  }

  lifecycle {
    ignore_changes = [time_period]
  }
}
