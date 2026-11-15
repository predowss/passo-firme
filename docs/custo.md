# Estimativa de custo

Região: `brazilsouth` (São Paulo). A estimativa usa preços de lista de novembro de 2026, em dólar, sem descontar as cotas gratuitas. O custo real, medido no Cost Management do grupo `rg-passofirme`, ficou muito abaixo dela.

## Custo real (Cost Management)

De 9 a 14 de novembro, com tudo no ar, o grupo custou **R$ 4,54** (moeda da assinatura):

| Recurso | Custo real | Por quê |
| --- | --- | --- |
| Container Registry Basic | R$ 4,14 | Tarifa diária fixa: é quase todo o custo |
| Zona de DNS privado | R$ 0,40 | Tarifa mensal por zona |
| PostgreSQL Flexible B1ms | R$ 0 | Dentro da cota gratuita da assinatura de estudante: 750 horas por mês da B1MS, 32 GB de armazenamento e 32 GB de backup, por 12 meses |
| Container Apps (API) | não aparece | Com escala a zero, o uso ficou dentro da cota gratuita mensal, e uso gratuito não entra na fatura |
| Log Analytics, alertas e grupo de ações | R$ 0 | — |

A partir de 14/11 a API ficou com 1 réplica sempre ligada para a correção. Ociosa, ela é cobrada na tarifa reduzida e passa da cota gratuita do mês: são uns US$ 3 a mais até o fim da correção. Somado ao Container Registry, a janela inteira da GS deve ficar perto de US$ 10. A tabela abaixo continua valendo como teto: é o custo de quem não tem os benefícios da assinatura.

## Premissas

- Assinatura Azure for Students, com US$ 100 de crédito.
- API com 0,5 vCPU e 1 GiB. Durante o desenvolvimento escalou a zero (`api_min_replicas = 0`); a partir de 14/11 ficou com 1 réplica sempre ligada (`api_min_replicas = 1`), para a correção.
- Tráfego de MVP, bem abaixo de 2 milhões de requisições por mês.
- Janela da GS: de 09/11 a cerca de 26/11 (fim da correção), uns 18 dias.

## Por recurso

| Recurso | Configuração | Custo mensal estimado | Observação |
| --- | --- | --- | --- |
| PostgreSQL Flexible | B1ms, 32 GiB | cerca de US$ 26 de computação + armazenamento | É o item mais caro. Em `brazilsouth` a computação custa cerca do dobro das regiões mais baratas dos EUA (US$ 12) |
| Container Apps (API) | 0,5 vCPU / 1 GiB | de US$ 0 (escala a zero, dentro da cota gratuita) a cerca de US$ 10 a 15 (1 réplica sempre ligada) | Cota gratuita mensal: 180.000 vCPU-s, 360.000 GiB-s e 2 milhões de requisições |
| Container Registry | Basic | cerca de US$ 5 | Tarifa diária fixa (US$ 0,167 por dia como referência) |
| Log Analytics | 30 dias, teto de 1 GB/dia | próximo de zero | Volume de log de MVP fica dentro da faixa gratuita |
| Alertas de métrica | 3 regras | menos de US$ 1 | — |
| VNet, NSG, DNS privado | — | menos de US$ 1 | VNet e NSG não são cobrados |
| State do Terraform | Storage Account | centavos | — |
| **Total** | | **cerca de US$ 35 a 50 por mês** | |
| **Janela da GS (18 dias)** | | **cerca de US$ 20 a 30** | Folga grande dentro dos US$ 100 |

### Como calcular o Container Apps

Container Apps cobra por segundo de vCPU e de memória alocadas, com tarifa menor quando a réplica está ociosa. Como referência, a tarifa de lista em East US é de US$ 0,000024 por vCPU-segundo ativo, US$ 0,000003 por vCPU-segundo ocioso e US$ 0,000003 por GiB-segundo. Em `brazilsouth` as tarifas são maiores.

Uma réplica ociosa de 0,5 vCPU e 1 GiB por 30 dias (2.592.000 s), na tarifa de referência:

- vCPU: 0,5 × 2.592.000 = 1.296.000; menos 180.000 grátis = 1.116.000 × 0,000003 = US$ 3,35
- Memória: 1 × 2.592.000 = 2.592.000; menos 360.000 grátis = 2.232.000 × 0,000003 = US$ 6,70

Só na semana de correção (7 dias) com 1 réplica ligada, o custo fica perto de US$ 1 a 2.

As tarifas exatas de `brazilsouth` vêm da API pública de preços da Azure:

```bash
curl -s -G "https://prices.azure.com/api/retail/prices" \
  --data-urlencode "\$filter=serviceName eq 'Azure Container Apps' and armRegionName eq 'brazilsouth' and priceType eq 'Consumption'" \
  | python3 -c "import json,sys; [print(i['meterName'], i['unitOfMeasure'], i['retailPrice']) for i in json.load(sys.stdin)['Items']]"
```

## O que pode estourar

| Item | Impacto | Como controlar |
| --- | --- | --- |
| LLM da IA Generativa no Container Apps (2 vCPU / 4 GiB) | Dezenas de dólares por mês com 1 réplica sempre ligada | Escala a zero no desenvolvimento e 1 réplica só na semana de correção |
| Banco esquecido ligado depois da GS | Cerca de US$ 30 por mês | `terraform destroy` depois de 26/11, ou `az postgres flexible-server stop` |
| Prometheus local coletando o tempo todo | Mantém a réplica da API acordada | Parar com `docker compose --profile obs stop prometheus grafana` depois dos prints |
| Recursos de projetos antigos na mesma assinatura | Consomem o mesmo crédito | Conferir o Cost Management e apagar os grupos de recursos que não são mais usados |
| Log descontrolado | Ingestão cobrada por GB | Teto diário de 1 GB no workspace |

## Proteções no código

- Escala a zero por padrão ([variables.tf](../infra/variables.tf)).
- Teto de ingestão de logs ([main.tf](../infra/main.tf)).
- Orçamento com aviso por e-mail em 50%, 80% e 100% (`orcamento_mensal_usd`), quando a assinatura permitir budgets.
- Tudo é recriável: `terraform destroy` no fim e `terraform apply` para voltar.

## Fontes

- [Preços do Azure Container Apps](https://azure.microsoft.com/pricing/details/container-apps/) e [cobrança do Container Apps](https://learn.microsoft.com/azure/container-apps/billing)
- [Preço do PostgreSQL Flexible B1ms por região (Bytebase)](https://www.bytebase.com/dbcost/azure-flexible/instance/B1ms/)
- [Camadas do Azure Container Registry](https://learn.microsoft.com/azure/container-registry/container-registry-skus)
- [API de preços de varejo da Azure](https://learn.microsoft.com/rest/api/cost-management/retail-prices/azure-retail-prices)
- [Azure for Students e serviços gratuitos](https://azure.microsoft.com/free/students/)
- [PostgreSQL Flexible na conta gratuita (750 horas da B1MS)](https://learn.microsoft.com/azure/postgresql/flexible-server/how-to-deploy-on-azure-free-account)
