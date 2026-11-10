# Estimativa de custo

Preços de lista em dólar na região East US 2, consultados em novembro de 2026. Confira no [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) e acompanhe o gasto real em Cost Management, porque preço e créditos variam por oferta.

## Premissas

- Assinatura Azure for Students, com US$ 100 de crédito.
- API com 0,5 vCPU e 1 GiB. Durante o desenvolvimento escala a zero (`api_min_replicas = 0`); na semana de correção fica com 1 réplica sempre ligada.
- Tráfego de MVP, bem abaixo de 2 milhões de requisições por mês.
- Janela da GS: de 09/11 a cerca de 26/11 (fim da correção), uns 18 dias.

## Por recurso

| Recurso | Configuração | Custo mensal estimado | Observação |
| --- | --- | --- | --- |
| Container Apps (API) | 0,5 vCPU / 1 GiB, 1 réplica sempre ligada e ociosa | cerca de US$ 10 | Com escala a zero, cabe na cota gratuita mensal |
| PostgreSQL Flexible | B1ms, 32 GiB | cerca de US$ 12 de computação + armazenamento | Pode sair de graça: a Azure for Students inclui 750 h/mês de B1MS com 32 GB por 12 meses para clientes novos |
| Container Registry | Basic | cerca de US$ 5 | Tarifa fixa de US$ 0,167 por dia |
| Log Analytics | 30 dias, teto de 1 GB/dia | próximo de zero | Volume de log de MVP fica dentro da faixa gratuita |
| Alertas de métrica | 3 regras | menos de US$ 1 | — |
| VNet, NSG, DNS privado | — | menos de US$ 1 | VNet e NSG não são cobrados |
| **Total sem gratuidades** | | **cerca de US$ 30 por mês** | |
| **Janela da GS (18 dias)** | | **cerca de US$ 15 a 20** | Folga grande dentro dos US$ 100 |

### Como chegamos no valor da API

Container Apps cobra US$ 0,000024 por vCPU-segundo ativo, US$ 0,000003 por vCPU-segundo ocioso e US$ 0,000003 por GiB-segundo. Todo mês os primeiros 180.000 vCPU-segundos, 360.000 GiB-segundos e 2 milhões de requisições são grátis.

Uma réplica ociosa de 0,5 vCPU e 1 GiB por 30 dias (2.592.000 s):

- vCPU: 0,5 × 2.592.000 = 1.296.000; menos 180.000 grátis = 1.116.000 × 0,000003 = **US$ 3,35**
- Memória: 1 × 2.592.000 = 2.592.000; menos 360.000 grátis = 2.232.000 × 0,000003 = **US$ 6,70**

Só na semana de correção (7 dias) com 1 réplica ligada, o custo fica em torno de **US$ 1,10**.

## O que pode estourar

| Item | Impacto | Como controlar |
| --- | --- | --- |
| LLM da IA Generativa no Container Apps (2 vCPU / 4 GiB) | Cerca de US$ 47 por mês com 1 réplica sempre ligada | Escala a zero no desenvolvimento e 1 réplica só na semana de correção (cerca de US$ 11) |
| Banco esquecido ligado depois da GS | US$ 12 a 16 por mês | `terraform destroy` depois de 26/11, ou `az postgres flexible-server stop` |
| Log descontrolado | Ingestão cobrada por GB | Teto diário de 1 GB no workspace |

## Proteções no código

- Escala a zero por padrão ([variables.tf](../infra/variables.tf)).
- Teto de ingestão de logs ([main.tf](../infra/main.tf)).
- Orçamento com aviso por e-mail em 50%, 80% e 100% (`orcamento_mensal_usd`), quando a assinatura permitir budgets.
- Tudo é recriável: `terraform destroy` no fim e `terraform apply` para voltar.

## Fontes

- [Preços do Azure Container Apps](https://azure.microsoft.com/pricing/details/container-apps/) e [cobrança do Container Apps](https://learn.microsoft.com/azure/container-apps/billing)
- [Camadas do Azure Container Registry](https://learn.microsoft.com/azure/container-registry/container-registry-skus)
- [Preço do PostgreSQL Flexible B1ms por região (Bytebase)](https://www.bytebase.com/dbcost/azure-flexible/instance/B1ms/)
- [Azure for Students: crédito e serviços gratuitos](https://azure.microsoft.com/free/students/)
