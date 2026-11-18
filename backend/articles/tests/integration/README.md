# Testes de integração (AWS real)

Os testes de `unit/` simulam a AWS. Estes usam os recursos reais e pegam o que a simulação não pega: senha errada, Security Group fechado, permissão ausente, nome de recurso errado, tipo de chave do DynamoDB, credencial expirada.

Três tipos:

- **Por serviço** (`test_rds.py`, `test_s3.py`, `test_dynamodb.py`, `test_redis.py`): o código do projeto fala com o serviço de verdade. Criam os próprios dados e apagam no fim.
- **Da configuração** (`test_especificacao.py`): só lê. Confere que cada recurso criado tem a configuração que a aplicação espera, requisito por requisito, incluindo o ALB e o Auto Scaling.
- **Ponta a ponta** (`test_pipeline_e2e.py`): cadastro, S3, DynamoDB, worker, cache, download e DELETE, pela API.

## Como rodar

```
cd backend && source .venv/bin/activate
set -a; source .env; set +a
RUN_AWS_INTEGRATION=1 python manage.py test articles.tests.integration                  # tudo
RUN_AWS_INTEGRATION=1 python manage.py test articles.tests.integration.test_rds         # um arquivo
RUN_AWS_INTEGRATION=1 RUN_AWS_INTEGRATION_SLOW=1 python manage.py test articles.tests.integration   # com os lentos
```

Sem `RUN_AWS_INTEGRATION=1`, tudo é pulado (`skipped`) e nada é cobrado. Cada classe se pula sozinha se faltar uma variável do `.env`, e a mensagem diz qual.

## Variáveis de cada arquivo

| Arquivo | Variáveis | Roda de onde |
|---|---|---|
| `test_rds.py` | `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | EC2, ou sua máquina com o IP liberado no `sg-rds` |
| `test_s3.py` | `S3_BUCKET` | Qualquer lugar com credenciais |
| `test_dynamodb.py` | `DYNAMODB_TABLE` | Qualquer lugar com credenciais |
| `test_rabbitmq.py` | Com o RabbitMQ no ar: `RUN_RABBITMQ_INTEGRATION=1`, `RABBITMQ_HOST`, `RABBITMQ_DEFAULT_USER`, `RABBITMQ_DEFAULT_PASS`. Não usa AWS e tem o próprio liga/desliga; usa fila temporária | Onde o broker for alcançável |
| `test_redis.py` | `REDIS_URL` | **Só da EC2** (o Redis fica dentro da VPC) |
| `test_pipeline_e2e.py` | `API_BASE_URL`, `S3_BUCKET`, `DYNAMODB_TABLE`, `REDIS_URL` (e `E2E_USERNAME`, `E2E_PASSWORD`) | EC2, com API e worker no ar |
| `test_especificacao.py` | ver a tabela abaixo | Qualquer lugar com credenciais (o do Redis, só da EC2) |

## O que `test_especificacao.py` confere

| Grupo | Variáveis | O que confere |
|---|---|---|
| Requisito 1, EC2 | `API_BASE_URL` (opcionais: `API_INSTANCE_NAME`, `WORKER_INSTANCE_NAME`, padrão `api` e `worker`) | `/health/` responde; instância `t2` ou `t3` micro ou small; com instance profile; worker em outra instância; 5432 e 6379 fechadas para a internet |
| Requisito 2, RDS | `RDS_INSTANCE_ID`, `DB_HOST` | Disponível, PostgreSQL, `DB_HOST` é o endpoint dela, banco `metadata`, classe `db.t*`, sem Multi-AZ |
| Requisito 3, S3 | `S3_BUCKET` | Na região certa, bloqueio de acesso público ligado, criptografia em repouso |
| Requisito 4, ElastiCache | `ELASTICACHE_ID`, `REDIS_URL` | Disponível, Redis, `REDIS_URL` aponta para ela, sem criptografia em trânsito, `ping` |
| Requisito 5, DynamoDB | `DYNAMODB_TABLE` | `ACTIVE`, sob demanda, chave `article_id` e `timestamp` (String) |
| Requisito 6, SNS e SQS | `SNS_TOPIC_ARN`, `SQS_QUEUE_URL`, `SQS_DLQ_URL` | Fila assinada no tópico com entrega bruta, política permite o tópico, long polling de 20 s, visibilidade de pelo menos 60 s, DLQ com 3 tentativas e 14 dias |
| Requisito 7, interface | `FRONT_URL`, `API_BASE_URL` | Site abre, as 8 telas existem, `config.js` aponta para a API da nuvem, a API autoriza a origem do site por CORS |
| Parte 2 | `ASG_NAME`, `ALB_NAME` | Grupo de 1 a 3 instâncias micro ou small; ALB público na porta 80; health check em `/health/` e alvo saudável; alarme de CPU acima de 70% por 1 minuto adiciona instância; alarme abaixo de 25% por 1 minuto remove |

O teste da Parte 2 espera política **simples ou em passos** ligada a alarmes do CloudWatch. Uma política de rastreamento de destino (target tracking) cria alarmes com outros limites e vai falhar de propósito: a regra de 70% e 25% é explícita. Ele confere a configuração, não a elasticidade: subir e descer instâncias sob carga se demonstra no vídeo.

## Regras

1. Cada teste cria os próprios dados, confere e limpa no fim (`addCleanup`). Ids de teste começam em 900000000.
2. Nunca grave dado real nem apague o que o teste não criou.
3. Nenhuma senha ou chave no código: tudo vem do `.env`.
