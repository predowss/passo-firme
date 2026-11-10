# Roteiro de evidências para o PDF (14 pontos)

O PDF é único, com links clicáveis, enviado no portal da disciplina até 19/11, às 23h55, por um só integrante. Cada print precisa estar legível, com legenda e, quando fizer sentido, com data e hora visíveis.

## Estrutura sugerida do PDF

1. Capa: Passo Firme, disciplina, nome completo e RM de todos.
2. Links: repositório, URL pública do MVP, `/docs` e `/health`, última execução verde do pipeline.
3. Arquitetura: diagrama do README, tabela de componentes e fluxos de rede ([arquitetura.md](arquitetura.md)).
4. Container e IaC: evidências da seção A.
5. Pipeline DevSecOps: evidências da seção B.
6. Observabilidade: evidências da seção C.
7. Responsabilidade compartilhada ([responsabilidade-compartilhada.md](responsabilidade-compartilhada.md)).
8. Dados pessoais e LGPD ([lgpd.md](lgpd.md)).
9. Custo ([custo.md](custo.md)) com um print do Cost Management.
10. Como reproduzir: link para o README.

## A. Container e IaC (5,0)

| Critério | Evidência | Como gerar |
| --- | --- | --- |
| Dockerfile enxuto (2,0) | Dockerfile comentado e tamanho da imagem | Print de [api/Dockerfile](../api/Dockerfile) e de `docker images passo-firme-api` |
| Usuário não root | Saída `uid=10001(app)` | `docker run --rm --entrypoint id passo-firme-api:local` |
| Sem segredo na imagem | Variáveis da imagem sem senha; Trivy sem segredo | `docker history --no-trunc passo-firme-api:local` e log do job de imagem |
| Stack com docker compose | Todos os serviços `healthy` | `docker compose up -d --build` e depois `docker compose ps` |
| Nuvem criada por Terraform (3,0) | Fim do apply e lista de outputs | `terraform apply` e `terraform output`; print do grupo de recursos no Portal |
| State e .tfvars fora do repo | Busca vazia no Git e blob do state no Storage | `git ls-files \| grep -E 'tfstate\|tfvars$'` (sem resultado) e print do container `tfstate` |
| Porta admin nunca aberta para 0.0.0.0/0 | Nenhuma VM; regras do NSG; banco com acesso privado | `az network nsg rule list -g rg-passofirme --nsg-name nsg-passofirme-db -o table` e print de "Networking" do Postgres |

## B. Pipeline DevSecOps (4,0)

| Critério | Evidência | Como gerar |
| --- | --- | --- |
| Build, Gitleaks, Semgrep e Trivy a cada push | Grafo de uma execução verde com os 6 jobs | Aba Actions, execução da `main` |
| Segredos em GitHub Secrets | Lista de Secrets do environment `producao` (os valores aparecem ocultos) | Settings > Environments > producao |
| Deploy automático | Job de deploy com a URL e o teste de fumaça mostrando a versão (SHA) | Log do passo "Teste de fumaça" e `/health` aberto no navegador |
| Execução barrada (caso real) | Execução #24 com "Build + Trivy" vermelho e a tabela do Trivy: `zlib1g`, CVE-2026-85091 (HIGH) | Já capturada ([lições aprendidas](licoes-aprendidas.md)) |
| Execução corrigida (caso real) | Trecho do Dockerfile com a correção e a execução #25 com a imagem aprovada | Já capturada |
| Demonstração extra (opcional) | Gitleaks barrando uma chave falsa e a correção | `./scripts/demo-pipeline-barrado.sh segredo` e depois `corrigir` |

O caso real do Trivy vale mais do que a demonstração: a vulnerabilidade estava na imagem oficial do Python e foi barrada antes de chegar à produção. Se fizer também a demonstração do segredo, explique no PDF por que apagar o arquivo num commit novo não basta: o segredo continua no histórico. Por isso o script reescreve o histórico, e num caso real a chave seria revogada na hora.

## C. Observabilidade (3,0)

| Critério | Evidência | Como gerar |
| --- | --- | --- |
| Painel com as 4 métricas de ouro | Painel "Passo Firme — 4 métricas de ouro" com dados do ambiente `api-azure` | `./scripts/configurar-prometheus.sh`, depois `for i in $(seq 30); do ./scripts/smoke-test.sh >/dev/null; done` |
| Alerta disparado | Alerta "Fired" no Azure Monitor, o detalhe com o gráfico (10 respostas 5xx contra o limite de 5) e o e-mail "Fired: Sev1" recebido | `./scripts/disparar-alerta.sh` e Portal > Monitor > Alerts |
| Notificação configurada | Grupo de ações com o e-mail "Verified" | Portal > Monitor > Alerts > Action groups |
| Alerta disparado (Prometheus) | `APIErros5xx` em FIRING e o painel "Alertas disparando" | http://localhost:9090/alerts e o Grafana |
| Recuperação | Erros 5xx de volta a 0% e `APIErros5xx` inativo; e-mail "Resolved" se chegar | Gerar tráfego normal com o smoke-test por 2 minutos |

## D. Documentação (2,0)

- Diagrama da arquitetura: README e [arquitetura.md](arquitetura.md).
- Responsabilidade compartilhada: [responsabilidade-compartilhada.md](responsabilidade-compartilhada.md).
- Dados pessoais (LGPD): [lgpd.md](lgpd.md).
- Estimativa de custo: [custo.md](custo.md).
- Lições aprendidas: [licoes-aprendidas.md](licoes-aprendidas.md).
- README reproduzível: peça para alguém de fora da trilha seguir o README do zero e anote o que travou.

## Checklist antes de enviar

- [x] Nome completo e RM de todos no README.
- [ ] Nome completo e RM de todos no PDF.
- [x] Ficha Técnica do MVP no README.
- [ ] Repositório público e URL do MVP abrindo numa janela anônima.
- [ ] `api_min_replicas = 1` aplicado para a semana de correção.
- [ ] Todos os links do PDF testados.
- [ ] Nenhum print com token, senha ou e-mail de integrante à mostra.
