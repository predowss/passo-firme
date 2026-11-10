# Registro privado das imagens. Sem usuário admin: o Container App puxa a imagem
# com uma identidade gerenciada (AcrPull) e o pipeline envia com outra (AcrPush).

resource "azurerm_container_registry" "main" {
  name                = "acr${local.nome}${random_string.sufixo.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}

# Identidade da API: só lê imagens do ACR.
resource "azurerm_user_assigned_identity" "api" {
  name                = "id-${local.nome}-api"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

resource "azurerm_role_assignment" "api_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
  principal_type       = "ServicePrincipal"
}
