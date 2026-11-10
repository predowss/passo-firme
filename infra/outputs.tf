output "api_url" {
  description = "URL pública do MVP (HTTPS)."
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "resource_group" {
  value = azurerm_resource_group.main.name
}

output "container_app" {
  value = azurerm_container_app.api.name
}

output "acr_name" {
  value = azurerm_container_registry.main.name
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "postgres_fqdn" {
  description = "Nome privado do banco (só resolve de dentro da VNet)."
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "github_repositorio" {
  value = var.github_repositorio
}

output "github_ambiente" {
  value = var.github_ambiente
}

# Identificadores (não são segredos) que o pipeline usa no azure/login via OIDC.
output "azure_client_id" {
  value = azurerm_user_assigned_identity.github.client_id
}

output "azure_tenant_id" {
  value = data.azurerm_client_config.atual.tenant_id
}

output "azure_subscription_id" {
  value = data.azurerm_client_config.atual.subscription_id
}

output "metrics_token" {
  description = "Token Bearer do /metrics (para o Prometheus local)."
  value       = random_password.metrics_token.result
  sensitive   = true
}

output "ops_token" {
  description = "Token da rota que simula erro (para disparar o alerta)."
  value       = random_password.ops_token.result
  sensitive   = true
}
