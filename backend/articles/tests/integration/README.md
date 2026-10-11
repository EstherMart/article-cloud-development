# Testes de integração (AWS real)

Os testes de `unit/` simulam a AWS. Estes usam os recursos reais, então pegam o que os unitários não pegam:
senha errada, Security Group fechado, permissão da LabRole, nome de recurso errado e credencial expirada.

## Estado

Os testes estão escritos e **desligados**. Eles só rodam com `RUN_AWS_INTEGRATION=1`.
Eles acessam recursos AWS reais e precisam das variáveis e permissões descritas abaixo.

## Como rodar

```
cd backend && source .venv/bin/activate
set -a; source .env; set +a
RUN_AWS_INTEGRATION=1 python manage.py test articles.tests.integration                 # tudo
RUN_AWS_INTEGRATION=1 python manage.py test articles.tests.integration.test_rds        # um serviço
RUN_AWS_INTEGRATION=1 RUN_AWS_INTEGRATION_SLOW=1 python manage.py test articles.tests.integration   # com os lentos
```

Sem `RUN_AWS_INTEGRATION=1`, tudo é pulado. O `python manage.py test` comum mostra `skipped=6` e nunca gasta dinheiro.
Com a variável ligada, cada arquivo se pula sozinho se faltar uma variável do `.env`, e a mensagem diz qual.

## Variáveis de cada arquivo

| Arquivo | Serviço | Variáveis necessárias | Roda de onde |
|---|---|---|---|
| `test_rds.py` | RDS | `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | EC2, ou sua máquina com o IP liberado no `sg-rds` |
| `test_s3.py` | S3 | `S3_BUCKET` | Qualquer lugar com credenciais |
| `test_dynamodb.py` | DynamoDB | `DYNAMODB_TABLE` | Qualquer lugar com credenciais |
| `test_sns_sqs.py` | SNS, SQS, DLQ | `SNS_TOPIC_ARN`, `SQS_QUEUE_URL` (e `SQS_DLQ_URL` para o teste da DLQ) | Qualquer lugar. Pare o worker antes |
| `test_redis.py` | ElastiCache | `REDIS_URL` | **Só da EC2** (o Redis fica dentro da VPC) |
| `test_pipeline_e2e.py` | Fluxo completo | `API_BASE_URL`, `S3_BUCKET`, `DYNAMODB_TABLE`, `REDIS_URL` (e `E2E_USERNAME`, padrão `teste`) | EC2, com API e worker no ar |

`base.py` define `AwsIntegrationTestCase`, o decorador `@slow` e `novo_article_id()`. Cada classe lista suas variáveis em `REQUIRED_ENV`.

## O que cada arquivo prova

- **RDS:** responde `SELECT 1`, está no banco certo, usa SSL, o Django está em PostgreSQL (e não no SQLite), as 4 migrations estão aplicadas, as tabelas existem e a escrita funciona (em tabela temporária).
- **S3:** upload devolve `artigos/{id}.pdf`, a URL pré-assinada baixa o mesmo conteúdo, o `ContentType` é PDF, o acesso sem assinatura dá 403, a URL expira e o delete remove o objeto.
- **DynamoDB:** grava ação, dados e hora, o histórico sai em ordem, o log de DELETE persiste e números decimais são aceitos. Lê o tipo da chave na própria tabela.
- **SNS/SQS:** a publicação chega à fila com raw delivery, a mensagem não apagada volta e (lento) a que falha 3 vezes vai para a DLQ.
- **Redis:** `ping`, `get_or_set` chama o loader uma vez, TTL aplicado, `invalidate_article` apaga as chaves e o Redis fora do ar não derruba a API.
- **Fluxo completo:** cadastro com PDF, S3, DynamoDB, worker até `PROCESSADO`, cache na segunda leitura e DELETE que limpa o PDF.

## Regras

1. Cada teste cria os próprios dados, confere e limpa no fim (`addCleanup`). Ids de teste começam em 900000000.
2. Nunca grave dado real nem apague dado que o teste não criou.
3. Nenhuma senha ou chave no código. Tudo vem do `.env`.
4. RDS, ElastiCache e EC2 cobram por hora. Ligue os testes só quando os recursos existirem e apague os recursos depois.
5. `test_sns_sqs.py` lê a fila real. Rode com o worker parado, de preferência numa fila só de teste.
6. `test_pipeline_e2e.py` ainda precisa ser alinhado ao POST autenticado atual: obtenha um token e envie `authors` e `tags` como listas JSON no multipart.
