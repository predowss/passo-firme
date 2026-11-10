# Passo a passo da trilha DevOps e Cloud

Alinhado ao plano do grupo: Marco 1 (MVP no ar com CI/CD) em 11/11, Marco 2 (as 7 peças respondendo) em 14/11, Marco 3 (vídeos com o MVP real) em 17/11, entrega em 19/11.

## 09/11 (seg): repositório e container

1. Criar a organização no GitHub e o repositório público `passo-firme` com o conteúdo desta pasta.
2. Testar localmente:
   ```bash
   ./scripts/gerar-env-local.sh
   docker compose up -d --build
   docker compose ps                      # db e api "healthy"
   ./scripts/smoke-test.sh http://localhost:8080
   docker run --rm --entrypoint id passo-firme-api:local   # uid=10001(app)
   ```
3. Primeiro push: o pipeline roda os jobs de segurança e testes. O deploy ainda falha por falta de configuração da Azure, e tudo bem.
4. Proteger a `main`: Settings > Branches > exigir pull request e os checks `Segredos (Gitleaks)`, `SAST (Semgrep)`, `IaC (Terraform + Trivy config)`, `Testes (pytest)` e `Build + Trivy (imagem)`.

## 10/11 (ter): Terraform

1. `az login` com a conta Azure for Students.
2. `LOCATION=eastus2 ./scripts/01-bootstrap-azure.sh`. Confira na saída as regiões liberadas; se `eastus2` não estiver na lista, rode de novo com uma região liberada.
3. Editar `infra/terraform.tfvars`: `github_repositorio` exatamente como aparece no GitHub (maiúsculas contam) e os e-mails dos alertas.
4. Aplicar:
   ```bash
   cd infra
   terraform init -backend-config=backend.hcl
   terraform plan -out tfplan
   terraform apply tfplan                 # 10 a 15 minutos (o Postgres é o mais lento)
   terraform output
   ```
5. Versionar o `infra/.terraform.lock.hcl` gerado no init.

## 11/11 (qua): pipeline e Marco 1

1. `./scripts/02-configurar-github.sh` cria o environment `producao` (deploy só da `main`) e grava Secrets e Variables.
2. Push na `main`: os 6 jobs ficam verdes e o deploy mostra a URL.
3. Abrir `terraform output -raw api_url` + `/health` e conferir a versão (SHA do commit).
4. Avisar o grupo da URL. Ela entra na Ficha Técnica e no README de todos os repositórios.

## 12/11 (qui): execução barrada e corrigida

```bash
./scripts/demo-pipeline-barrado.sh segredo     # print do Gitleaks vermelho
./scripts/demo-pipeline-barrado.sh corrigir    # print da mesma branch verde
git switch main
./scripts/demo-pipeline-barrado.sh vulnerabilidade
./scripts/demo-pipeline-barrado.sh corrigir
```

## 13/11 (sex): serviços de IA

Com as trilhas de Visão e IA: cada serviço vira um Container App interno no mesmo ambiente, a partir de uma imagem no ACR. Medir memória e tempo de resposta com o modelo quantizado em CPU, e acompanhar o custo ([custo.md](custo.md)).

## 14/11 (sáb): observabilidade e Marco 2

```bash
./scripts/configurar-prometheus.sh             # Prometheus + Grafana locais apontando para a Azure
for i in $(seq 30); do ./scripts/smoke-test.sh >/dev/null; done
./scripts/disparar-alerta.sh                   # alerta do Azure Monitor + e-mail
```

Prints do painel, do alerta disparado e do e-mail.

## 16/11 (seg): endurecimento

- `cors_origins` com a URL do app web em `terraform.tfvars`, depois `terraform apply`.
- Conferir os cabeçalhos: `curl -sI https://SUA-URL/health` mostra HSTS e nosniff.
- Revisar [lgpd.md](lgpd.md) com a trilha de Produto.

## 17/11 (ter): custo e correção

- Print do Cost Management do grupo `rg-passofirme`.
- `api_min_replicas = 1` em `terraform.tfvars` e `terraform apply`, para o MVP responder rápido durante a correção.

## 18/11 e 19/11: PDF e envio

Seguir o [roteiro de evidências](evidencias.md). Testar todos os links numa janela anônima antes de enviar.

## Depois da correção (a partir de 27/11)

```bash
cd infra && terraform destroy
az group delete --name rg-passofirme-tfstate
```

## Problemas comuns

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| `RequestDisallowedByAzure` | Região fora da lista da Azure for Students | Trocar `location` por uma região permitida (o bootstrap mostra a lista) |
| Postgres falha com restrição de região ou oferta | Postgres indisponível para a assinatura naquela região | Trocar `location` e rodar o apply de novo |
| `AADSTS700213` ou "no matching federated identity" no deploy | Subject do OIDC diferente | `github_repositorio` com as maiúsculas exatas e o job rodando no environment `producao` |
| `AuthorizationFailed` no deploy | Papel ainda propagando | Esperar 5 minutos e reexecutar o job |
| `terraform init` sem permissão no state | Falta o papel no Storage Account | Dar "Storage Blob Data Contributor" a quem roda o Terraform |
| Job IaC falha no `fmt` | Arquivo .tf fora do padrão | `terraform fmt -recursive infra` e commit |
| Trivy acusa CVE na imagem base | Base desatualizada | Rodar o pipeline de novo (o build pega a base mais nova) ou aceitar o PR do Dependabot |
| Trivy (config) acusa algo que já está tratado, como TLS no Postgres Flexible, que vem ligado por padrão | Regra feita para outro tipo de recurso | Registrar o ID no `.trivyignore` com justificativa e data de revisão; nunca desligar o job |
| Semgrep acusa falso positivo | Regra genérica | `# nosemgrep: <id-da-regra>` na linha, com um comentário explicando o motivo |
| Container App não sobe a imagem do ACR (401) | AcrPull ainda propagando | Esperar alguns minutos e reexecutar o deploy |
| Primeira resposta demora uns 10 s | Escala a zero | Normal no desenvolvimento; `api_min_replicas = 1` na correção |
