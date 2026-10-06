# articles/services

Uma camada fina por serviço AWS. As views só orquestram e chamam estas funções. Quem implementa o S3 mexe só em `s3.py`, quem faz o cache só em `cache.py`, e assim as branches não conflitam.

| Arquivo | Serviço | Branch |
|---|---|---|
| `aws.py` | fábrica de clientes boto3 | compartilhado |
| `s3.py` | S3 | `feat/s3-upload` |
| `dynamo_log.py` | DynamoDB | `feat/log-dynamodb` |
| `cache.py` | ElastiCache (Redis) | `feat/cache-redis` |
| `messaging.py` | SNS | `feat/sns-sqs-worker` |

## Estado

Só o esqueleto existe: cada função tem a assinatura, um docstring com as regras e `raise NotImplementedError`. O docstring diz como implementar. Mantenha a assinatura. Se precisar mudar, avise o grupo, porque as views dependem dela.

## Como usar nas views

Ordem do `POST /articles/` (detalhes em `../../README.md`):

```python
from articles.services import s3, dynamo_log, cache, messaging

article = Article.objects.create(..., processing_status='PENDENTE')   # RDS
article.s3_key = s3.upload_pdf(article.id, arquivo)                  # S3
article.save()
dynamo_log.log_action('CREATE', article.id, dados)                   # DynamoDB
cache.invalidate_article(article.id)                                 # Redis
messaging.publish_article_created(article.id, article.s3_key, bucket) # SNS
```

## Regras comuns

- Nenhuma chave de acesso no código. Use a IAM Role (LabRole) e as variáveis do `.env`.
- Os imports do boto3 e do redis são feitos dentro das funções, para o projeto importar sem eles.
- Falha no cache nunca derruba a API. Falha no S3 desfaz o cadastro.
- Quando a tarefa terminar, atualize a tabela de status do README da raiz.
