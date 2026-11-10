# Deploy sem senha: o GitHub Actions troca um token OIDC de curta duração por um
# acesso à Azure. A confiança vale só para o environment "producao" deste
# repositório; nenhum segredo de longo prazo fica guardado no GitHub.
# Usa identidade gerenciada (não precisa de permissão para criar app registration,
# o que costuma ser bloqueado em contas de estudante).

resource "azurerm_user_assigned_identity" "github" {
  name                = "id-${local.nome}-github-deploy"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

resource "azurerm_federated_identity_credential" "github" {
  name                = "github-${var.github_ambiente}"
  resource_group_name = azurerm_resource_group.main.name
  parent_id           = azurerm_user_assigned_identity.github.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:${var.github_repositorio}:environment:${var.github_ambiente}"
}

# Escopo restrito ao grupo de recursos do projeto, nunca à assinatura inteira.
resource "azurerm_role_assignment" "github_contributor" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "github_acr_push" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPush"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
  principal_type       = "ServicePrincipal"
}
