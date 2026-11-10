# Modelo de responsabilidade compartilhada

O Passo Firme usa só serviços PaaS: Azure Container Apps, PostgreSQL Flexible Server e Container Registry. A Azure cuida de tudo do sistema operacional para baixo; a equipe cuida do que roda em cima e de como está configurado.

| Camada | Azure | Equipe Passo Firme | Como a equipe cumpre a sua parte |
| --- | --- | --- | --- |
| Datacenter, energia, hardware | ✔ | | — |
| Rede física, hipervisor | ✔ | | — |
| Sistema operacional e Kubernetes do Container Apps | ✔ | | — |
| Certificado e terminação HTTPS do ingress | ✔ | Exigir HTTPS | `allow_insecure_connections = false` e HSTS na API |
| Motor do PostgreSQL: patches, backup, disponibilidade | ✔ | Escolher retenção e rede | Backup de 7 dias; acesso só privado; TLS obrigatório |
| Rede virtual: VNet, sub-redes, NSG, DNS privado | Fornece | ✔ Configura | Terraform em [rede.tf](../infra/rede.tf); banco sem IP público; nenhuma porta de administração |
| Identidades e permissões (RBAC) | Fornece | ✔ Configura | Identidades gerenciadas; papéis com escopo no grupo de recursos ou no ACR; OIDC no deploy |
| Segredos | Guarda criptografados | ✔ Gera, distribui e rotaciona | `random_password` no Terraform; secrets do Container App; nada em código, imagem ou Git |
| Imagem do container | | ✔ | Base slim, multi-stage, usuário não root, Trivy barra CVE alta ou crítica |
| Código da aplicação | | ✔ | Semgrep, testes, limite de requisições, validação de entrada e cabeçalhos de segurança |
| Cadeia de entrega (pipeline) | | ✔ | Gitleaks, permissões mínimas, versões fixas, actions de terceiros fixadas por SHA, Dependabot |
| Dados dos cidadãos (LGPD) | Infraestrutura com criptografia em repouso | ✔ Classifica, minimiza e protege | [lgpd.md](lgpd.md) |
| Monitoramento e resposta | Coleta métricas de plataforma | ✔ Define alertas e reage | Azure Monitor com e-mail, Prometheus e Grafana |
| Custo | Cobra pelo uso | ✔ Dimensiona e acompanha | Escala a zero, teto de logs, orçamento opcional ([custo.md](custo.md)) |

Resumo para o pitch e o PDF: com PaaS, a equipe não aplica patch de sistema operacional nem cuida de servidor. Em troca, cada erro de configuração é dela: rede, permissões, segredos, imagem e dados. É exatamente isso que o Terraform e o pipeline automatizam e verificam a cada push.
