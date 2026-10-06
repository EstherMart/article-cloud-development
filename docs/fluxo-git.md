# Fluxo de Git

## Regras

- A `main` sempre roda. Ninguém commita direto nela.
- Uma funcionalidade por branch, criada a partir da `main` atualizada.
- PR revisado por outra pessoa, com squash no merge.
- Antes do PR, faça rebase na `main`.
- Commits no formato `tipo: descrição` (`feat`, `fix`, `docs`, `chore`).

## Branches

| Branch | Conteúdo |
|---|---|
| `feat/db-postgres` | Conexão com o RDS e migrations. Entra primeiro, as outras dependem dela |
| `feat/crud-artigos` | POST, PUT, DELETE, GET e validação |
| `feat/s3-upload` | Upload do PDF, URL pré-assinada e `/download` |
| `feat/log-dynamodb` | Log das ações de CRUD |
| `feat/cache-redis` | Cache-aside e invalidação |
| `feat/sns-sqs-worker` | Publicação do evento e worker |
| `feat/frontend-integracao` | JavaScript do front |
| `infra/alb-asg` | Parte 2 |

## Estado das branches antigas

`django_init` e `telas` foram incorporadas à `main`. A `backend` era um subconjunto da `django_init` e pode ser apagada.

## Ordem sugerida

`feat/db-postgres` primeiro. Depois S3, DynamoDB e Redis em paralelo, porque são independentes entre si. O worker depende de S3, SNS/SQS e RDS. O ASG só funciona com a API completa rodando numa EC2.
