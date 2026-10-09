# Testes de integração (AWS real)

Os testes de `unit/` simulam a AWS. Estes aqui usam os recursos reais, então pegam o que os unitários não pegam:
senha errada, Security Group fechado, permissão da LabRole, nome de recurso errado e credencial expirada.

## Estado

Só o esqueleto existe. Cada arquivo tem, em comentário, o que o teste vai fazer. Descomente e implemente
quando o serviço estiver criado na AWS e implementado em `articles/services/`.

## Como vão rodar

```
cd backend && source .venv/bin/activate
set -a; source .env; set +a
RUN_AWS_INTEGRATION=1 python manage.py test articles.tests.integration
```

Sem `RUN_AWS_INTEGRATION=1`, os testes são pulados. O comando `python manage.py test` comum nunca gasta dinheiro.

## Regras

1. Cada teste cria os próprios dados, confere e limpa no fim (`addCleanup`). Use prefixos como `teste-integracao-`.
2. Nunca grave dado real nem apague dado que o teste não criou.
3. Nenhuma senha ou chave no código. Tudo vem do `.env`.
4. Um arquivo por serviço. Se o serviço não estiver criado, o teste é pulado com `skipUnless` (variável vazia).
5. Rode só quando os recursos existirem. RDS, ElastiCache e EC2 cobram por hora: teste e apague.

## Arquivos

| Arquivo | Serviço | Roda de onde |
|---|---|---|
| `base.py` | Regras comuns: liga e desliga os testes | - |
| `test_rds.py` | RDS PostgreSQL | EC2 ou sua máquina (com IP liberado) |
| `test_s3.py` | S3 | qualquer lugar com credenciais |
| `test_dynamodb.py` | DynamoDB | qualquer lugar com credenciais |
| `test_sns_sqs.py` | SNS e SQS (e DLQ) | qualquer lugar com credenciais |
| `test_redis.py` | ElastiCache | **só da EC2** (o Redis fica dentro da VPC) |
| `test_pipeline_e2e.py` | Fluxo completo: API, S3, DynamoDB, SNS, worker, RDS, Redis | EC2 |
