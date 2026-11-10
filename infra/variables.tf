variable "subscription_id" {
  description = "ID da assinatura Azure (az account show --query id -o tsv)."
  type        = string
}

variable "location" {
  description = "Região da Azure. Na Azure for Students, use uma das regiões liberadas pela política \"Allowed resource deployment regions\" da sua assinatura."
  type        = string
  default     = "eastus2"
}

variable "projeto" {
  description = "Prefixo dos nomes dos recursos (só letras minúsculas e números)."
  type        = string
  default     = "passofirme"

  validation {
    condition     = can(regex("^[a-z0-9]{3,12}$", var.projeto))
    error_message = "Use de 3 a 12 letras minúsculas ou números."
  }
}

variable "github_repositorio" {
  description = "Repositório que pode fazer deploy, no formato organizacao/repositorio (com as maiúsculas exatas do GitHub)."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repositorio))
    error_message = "Use o formato organizacao/repositorio."
  }
}

variable "github_ambiente" {
  description = "Environment do GitHub Actions autorizado a fazer deploy."
  type        = string
  default     = "producao"
}

variable "emails_alerta" {
  description = "E-mails que recebem os alertas do Azure Monitor. São dados pessoais: ficam só no terraform.tfvars, fora do Git."
  type        = list(string)
  default     = []
}

variable "imagem_inicial" {
  description = "Imagem pública usada só na criação do Container App; o pipeline troca pela imagem da API. Precisa escutar na porta 8080."
  type        = string
  default     = "mcr.microsoft.com/dotnet/samples:aspnetapp"
}

variable "api_min_replicas" {
  description = "Réplicas mínimas da API. 0 = escala a zero (mais barato, primeira resposta mais lenta). Use 1 durante a correção."
  type        = number
  default     = 0
}

variable "api_max_replicas" {
  description = "Réplicas máximas da API. O MVP usa 1 (limite de requisições e métricas em memória)."
  type        = number
  default     = 1
}

variable "api_cpu" {
  description = "vCPU da API."
  type        = number
  default     = 0.5
}

variable "api_memoria" {
  description = "Memória da API (combinação válida com a vCPU, ex.: 0.5 -> 1Gi)."
  type        = string
  default     = "1Gi"
}

variable "cors_origins" {
  description = "Origens liberadas no CORS, separadas por vírgula (URL do app web)."
  type        = string
  default     = ""
}

variable "limite_req_por_minuto" {
  description = "Limite de requisições por IP por minuto na API."
  type        = number
  default     = 120
}

variable "orcamento_mensal_usd" {
  description = "Orçamento mensal do grupo de recursos em USD, com aviso por e-mail em 50%, 80% e 100%. 0 = sem orçamento (algumas assinaturas de estudante não suportam budgets)."
  type        = number
  default     = 0
}

variable "tags" {
  description = "Tags extras aplicadas a todos os recursos."
  type        = map(string)
  default     = {}
}
