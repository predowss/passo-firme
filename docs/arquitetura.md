# Arquitetura de produção

O MVP roda inteiro em serviços gerenciados da Azure, na região `brazilsouth` (São Paulo), criados pelo Terraform da pasta [infra/](../infra). Não existe máquina virtual: não há SSH, RDP nem porta de administração para abrir.

O diagrama está no [README](../README.md#arquitetura-de-produção).

## Componentes

| Componente | Recurso Azure | Arquivo |
| --- | --- | --- |
| API do MVP | Container App `ca-passofirme-api` (perfil Consumption, 0,5 vCPU, 1 GiB) | [app.tf](../infra/app.tf) |
| Ambiente dos containers | Container Apps Environment `cae-passofirme`, dentro da VNet | [app.tf](../infra/app.tf) |
| Banco | PostgreSQL Flexible Server 16, B1ms, acesso privado | [banco.tf](../infra/banco.tf) |
| Rede | VNet `10.40.0.0/16`, sub-redes `snet-apps` e `snet-db`, NSG e DNS privado | [rede.tf](../infra/rede.tf) |
| Imagens | Azure Container Registry Basic, sem usuário admin | [registro.tf](../infra/registro.tf) |
| Identidades | `id-passofirme-api` (AcrPull) e `id-passofirme-github-deploy` (OIDC) | [registro.tf](../infra/registro.tf), [github-oidc.tf](../infra/github-oidc.tf) |
| Logs | Log Analytics, 30 dias, teto de 1 GB por dia | [main.tf](../infra/main.tf) |
| Alertas | Azure Monitor: 5xx, latência e CPU, com e-mail | [monitoramento.tf](../infra/monitoramento.tf) |
| State do Terraform | Storage Account próprio, criado pelo bootstrap | [01-bootstrap-azure.sh](../scripts/01-bootstrap-azure.sh) |

## Fluxos de rede

| Origem | Destino | Porta | Controle |
| --- | --- | --- | --- |
| Internet | API | 443 (HTTPS) | Ingress gerenciado; HTTP puro recusado (`allow_insecure_connections = false`) |
| API | PostgreSQL | 5432 | Rede privada; NSG libera só a `snet-apps`; TLS obrigatório |
| Internet | PostgreSQL | nenhuma | Servidor sem endpoint público (`public_network_access_enabled = false`) |
| Container App | ACR | 443 | Identidade gerenciada com papel AcrPull |
| GitHub Actions | Azure | 443 | Token OIDC válido só para o environment `producao` deste repositório |
| Prometheus da equipe | `/metrics` da API | 443 | Token Bearer exigido pela API |

## Decisões

| Decisão | Por quê | Evolução |
| --- | --- | --- |
| Região `brazilsouth` | Dados dos cidadãos no Brasil (LGPD, art. 33) e menor latência para São Paulo; está entre as regiões liberadas para a conta de estudante | Zona redundante para alta disponibilidade |
| Azure Container Apps em vez de VM ou AKS | HTTPS e certificado gerenciados, escala a zero, cota gratuita mensal e nenhum servidor para manter ou abrir para SSH | AKS se o número de serviços crescer muito |
| PostgreSQL gerenciado e privado | Backup automático de 7 dias e patches por conta da Azure; sem IP público, o banco não pode ser atacado direto da internet | Alta disponibilidade entre zonas |
| ACR com identidade gerenciada | Imagem privada e nenhuma senha de registro em lugar nenhum | Assinatura de imagem e varredura contínua no registro |
| OIDC com identidade gerenciada | O GitHub não guarda segredo de longo prazo. Usar identidade gerenciada em vez de app registration funciona mesmo quando a conta de estudante não pode criar aplicativos no Entra ID. A confiança usa o subject com os IDs imutáveis do dono e do repositório, então um repositório recriado com o mesmo nome não herda o acesso | Papel customizado com o mínimo de ações |
| Segredos do Container Apps gerados pelo Terraform | Senha do banco e tokens nascem aleatórios (`random_password`), ninguém os digita, e o código só os vê como variáveis de ambiente | Key Vault referenciado pela identidade da API |
| State remoto sem chave compartilhada | O state contém segredos: fica num Storage Account com acesso só pelo Entra ID, versionamento e retenção de exclusão | Bloqueio por rede privada |
| Prometheus e Grafana locais + Azure Monitor | O painel fica versionado como código e o enunciado permite rodá-lo local apontando para o MVP publicado. Os alertas do Azure Monitor avisam por e-mail mesmo com as máquinas da equipe desligadas | Grafana gerenciado ou Application Insights com OpenTelemetry |
| Escala de 0 a 1 réplica | Custo quase zero fora de uso. O limite de requisições e as métricas ficam em memória, o que pede uma réplica só | Limite no API gateway e métricas agregadas, para escalar horizontalmente |

## Como as outras trilhas entram

Todas as peças falam com a mesma API ([contrato v0](../api/app/main.py)). Hoje `/detectar` e `/assistente` devolvem respostas simuladas, com o formato final. Quando Visão e IA tiverem seus serviços, cada um vira um Container App interno no mesmo ambiente (ingress interno, sem acesso pela internet). A API passa a chamá-los pelo nome interno, e o pipeline de cada repositório publica a própria imagem no mesmo ACR.
