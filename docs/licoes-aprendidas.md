# Lições aprendidas no deploy

Problemas reais que apareceram ao colocar o MVP no ar, e como cada um foi resolvido. Todos ficaram registrados no código ou na documentação, para não se repetirem.

## 1. O Trivy barrou uma vulnerabilidade real na imagem base

| | |
| --- | --- |
| Sintoma | O job "Build + Trivy (imagem)" falhou na execução #24 com 2 achados HIGH. |
| Causa | O pacote `zlib1g` da imagem oficial `python:3.12-slim` (Debian 13) tinha a CVE-2026-85091, um estouro de memória que permite executar código. O Debian já tinha publicado a correção (`1.3.1-1+deb13u1`), mas a imagem base ainda não tinha sido reconstruída com ela. |
| Correção | O Dockerfile atualiza só esse pacote (`apt-get install --only-upgrade zlib1g`), com o motivo registrado num comentário. Na execução #25 o Trivy passou e a imagem foi liberada. |
| Lição | A imagem base "oficial" não é garantia de imagem segura. O scanner precisa rodar a cada build e barrar o deploy, e a correção pode ser cirúrgica, sem trocar a base inteira. |

## 2. O login OIDC do GitHub na Azure não reconhecia o repositório

| | |
| --- | --- |
| Sintoma | `AADSTS700213: No matching federated identity record found for presented assertion subject`. |
| Causa | O GitHub passou a incluir no token OIDC os IDs imutáveis do dono e do repositório: `repo:predowss@126830114/passo-firme@1452114405:environment:producao`. A credencial federada esperava o formato antigo, `repo:predowss/passo-firme:environment:producao`. |
| Correção | Variável `github_oidc_subject` no Terraform, preenchida a partir da API do GitHub. A credencial passou a aceitar exatamente o subject novo. |
| Lição | O formato novo é mais seguro: se o repositório for apagado e alguém criar outro com o mesmo nome, o novo não herda o acesso à Azure, porque o ID muda. |

## 3. O Terraform quis remover uma configuração que a Azure exige

| | |
| --- | --- |
| Sintoma | Um `terraform apply` sem nenhuma mudança na rede propôs remover o endpoint `Microsoft.Storage` da sub-rede do banco. |
| Causa | Ao criar o PostgreSQL com acesso privado, a própria Azure adiciona esse endpoint, que o banco usa para backups e logs. Como ele não estava no código, o Terraform via uma diferença e queria "corrigir". |
| Correção | O endpoint foi declarado em `infra/rede.tf`. O plano voltou a mostrar só a mudança pretendida. |
| Lição | Sempre ler o plano antes de digitar `yes`. Drift não é só alguém mudando algo no portal: o próprio provedor também altera recursos. |

## 4. O alerta disparou, mas o e-mail não chegou

| | |
| --- | --- |
| Sintoma | O alerta aparecia como "Fired" no Azure Monitor, mas nenhum e-mail chegava. |
| Causa | A Azure exige que cada e-mail cadastrado num grupo de ações seja verificado por um código válido por 30 minutos. O código venceu antes da verificação. |
| Correção | Verificação do e-mail no grupo de ações (status "Verified") e novo disparo de teste. O e-mail "Fired: Sev1" chegou. |
| Lição | Alerta que ninguém recebe não é alerta. O teste de ponta a ponta precisa incluir a notificação, não só a regra. |

## 5. O Dependabot lotou o pipeline no primeiro push

| | |
| --- | --- |
| Sintoma | Cerca de 20 execuções do pipeline em paralelo logo após criar o repositório, escondendo a execução da `main`. |
| Causa | O Dependabot abriu um PR por dependência, e cada PR rodava o pipeline duas vezes (push e pull request). Um dos PRs subia o provider azurerm para a versão 5, que quebraria o Terraform. |
| Correção | Atualizações agrupadas, no máximo 1 PR por ecossistema por mês, versão major do azurerm bloqueada, e o pipeline ignora o push das branches do Dependabot (que já roda pelo pull request). |
| Lição | Automação de atualização também precisa de governança; atualização major de provider de infraestrutura é decisão de equipe, não de robô. |

## 6. A conta de estudante restringe regiões

| | |
| --- | --- |
| Sintoma | `eastus2`, a região planejada, não estava liberada. |
| Causa | A Azure for Students limita cada assinatura a cerca de cinco regiões, que variam por pessoa. A nossa permitia `canadacentral`, `chilecentral`, `centralus`, `brazilsouth` e `northcentralus`. |
| Correção | O script de bootstrap mostra a lista antes de criar qualquer recurso, e a região virou variável. Escolhemos `brazilsouth`. |
| Lição | A restrição virou ganho: os dados dos cidadãos ficam no Brasil, sem transferência internacional (LGPD, art. 33), e a latência para São Paulo é a menor possível. |
