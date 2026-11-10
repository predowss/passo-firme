# Onde ficam os dados pessoais (LGPD)

Princípio adotado: guardar o mínimo, pelo menor tempo, no lugar mais fechado possível (LGPD, art. 6º: finalidade, necessidade e segurança).

## Mapa dos dados

| Dado | É pessoal? | Onde fica | Proteção | Retenção |
| --- | --- | --- | --- | --- |
| Coordenada do relato | Sim, quando ligada a uma pessoa | PostgreSQL privado (`relato.lat`, `relato.lon`) | Arredondada para 4 casas (cerca de 11 m): localiza a barreira, não a casa de ninguém. Banco sem IP público e com TLS | Enquanto a barreira estiver aberta, mais 12 meses para o indicador de tempo de conserto (proposta) |
| Identificador de quem relatou | Sim (pseudonimizado) | PostgreSQL (`relato.autor_hash`) | Só o HMAC-SHA256 com chave secreta (`AUTOR_SALT`); o identificador original nunca é gravado nem devolvido pela API | Igual ao relato |
| Foto da calçada | Pode conter rostos e placas | Não é guardada na v0 (`foto_url` vazio) | Quando for guardada: borramento de rostos e placas pela Visão Computacional antes de salvar, em armazenamento privado | A definir com a trilha de Visão |
| Descrição livre | Pode conter dado pessoal digitado | PostgreSQL (`relato.descricao`) | Limite de 500 caracteres; o app orienta a não escrever nome, telefone ou endereço | Igual ao relato |
| IP de quem acessa | Sim | Só em memória, para o limite de requisições | Não vai para banco nem para log: o log de acesso do uvicorn está desligado e o da API grava só método, rota, status e tempo | Some em até 1 minuto |
| Logs da aplicação | Não deveriam ter | Log Analytics | Sem IP, sem query string e sem corpo de requisição | 30 dias |
| Leituras do robô | Não | PostgreSQL (`leitura_robo`) | Coordenada arredondada | Igual ao relato |
| E-mails da equipe nos alertas | Sim | Action group do Azure Monitor e `terraform.tfvars` | O tfvars fica fora do Git | Até o fim do projeto |
| State do Terraform | Contém segredos (senha do banco, tokens) | Storage Account do state | Acesso só pelo Entra ID, sem chave compartilhada, com versionamento | Até o `terraform destroy` |
| Dados em prints e vídeos | Não deveriam ter | PDF e vídeos da GS | Usar só dados de teste (`scripts/smoke-test.sh`) | — |

## Pontos de atenção

- **Transferência internacional (art. 33):** a região padrão é `eastus2`, nos Estados Unidos, porque a assinatura de estudante restringe regiões e lá o custo é menor. Num piloto real com a prefeitura, a recomendação é `brazilsouth`, trocando a variável `location`.
- **Pseudonimizado continua sendo pessoal:** o hash do autor reduz o risco, mas ainda é dado pessoal (art. 12 e art. 13, § 4º). Por isso a chave fica só no secret do Container App.
- **Direitos do titular:** como o app não exige cadastro, o titular pode pedir a exclusão dos próprios relatos informando o identificador que o app gerou para ele.
- **Base legal:** a definir com o modelo de negócio. No piloto com cidadãos, consentimento no app (art. 7º, I). Numa parceria com o poder público, execução de políticas públicas (art. 7º, III).
