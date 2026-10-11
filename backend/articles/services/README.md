# articles/services

Uma camada fina por serviço AWS. As views só orquestram e chamam estas funções. Quem implementa o S3 mexe só em `s3.py`, quem faz o cache só em `cache.py`, e assim as branches não conflitam.

| Arquivo | Serviço | Branch |
|---|---|---|
| `aws.py` | fábrica de clientes boto3 | compartilhado |
| `s3.py` | S3 | `feat/s3-upload` |
| `dynamo_log.py` | DynamoDB | `feat/log-dynamodb` |
| `cache.py` | ElastiCache (Redis) | `feat/cache-redis` |
| `messaging.py` | SNS | `feat/sns-sqs-worker` |

## Uso

As funções de S3, DynamoDB, Redis e SNS são chamadas pelas views. O cadastro publica no SNS depois de salvar os metadados no RDS e enviar o PDF ao S3. A publicação usa `SNS_TOPIC_ARN`; se ela falhar, o artigo fica com status `ERRO` e a API devolve erro em vez de indicar sucesso.

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
- Falha no cache não deve derrubar a API. Falha no S3 interrompe o cadastro.
- A falha ao publicar no SNS é reportada; o artigo já salvo fica marcado como `ERRO`.
