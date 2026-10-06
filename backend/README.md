# Backend (API Django)

API REST em Django. Responsável por validar, gravar no RDS, enviar o PDF ao S3, logar no DynamoDB, usar o cache Redis e publicar no SNS.

## Estrutura

```
backend/
├── manage.py
├── requirements.txt
├── .env.example          modelo das variáveis de ambiente
├── article_cloud/        configuração do projeto (settings, urls, wsgi)
└── articles/             app principal
    ├── models.py         Article, Tag, Author
    ├── views.py          rotas da API (só orquestram)
    ├── urls.py           mapa de rotas
    └── services/         uma camada fina por serviço AWS (ver services/README.md)
        ├── aws.py            clientes boto3
        ├── s3.py             PDF
        ├── dynamo_log.py     log de CRUD
        ├── cache.py          Redis
        └── messaging.py      SNS
```

`services/` tem só o esqueleto: assinaturas, regras e como implementar, em comentários. As views chamam essas funções e não falam com a AWS diretamente.

Crescimento previsto: quando `views.py` ficar grande, vira o pacote `views/` e ganha `validators.py`. A autenticação (login, cadastro, perfil) vai para um app `accounts`.

## Rotas

| Método | Rota | Função | Estado |
|---|---|---|---|
| GET | `/articles/` | Lista artigos | implementado (sem paginação nem cache) |
| POST | `/articles/` | Cadastra artigo com PDF | stub |
| GET | `/articles/<id>/` | Detalhe | stub |
| PUT | `/articles/<id>/` | Atualiza | stub |
| DELETE | `/articles/<id>/` | Remove | stub |
| GET | `/articles/search/` | Busca | stub |
| GET | `/articles/<id>/download/` | URL pré-assinada do PDF | stub |

`/articles/search/` fica antes de `/articles/<id>/` no `urls.py` para a busca não ser confundida com um id.

## Modelo de dados (RDS) -- Necessário validar após tudo implementado

`Article`:

| Campo | Tipo | Observação |
|---|---|---|
| `id` | inteiro, PK | |
| `processing_status` | PENDENTE, PROCESSANDO, PROCESSADO, ERRO | padrão PENDENTE |
| `author` | texto | hoje um campo só; a spec fala em "autores" (decidir: lista ou M2M com `Author`) |
| `title` | texto, único | |
| `upload_datetime` | data e hora | automático |
| `user` | FK para `User` | |
| `area` | texto | |
| `tags` | M2M com `Tag` | |
| `abstract` | texto | resumo digitado no cadastro |
| `translated_abstract` | texto | preenchido pelo worker |
| `s3_key` | texto | chave do PDF no S3, preenchida após salvar o registro |

## Variáveis de ambiente

Copie `.env.example` para `.env`. O `.env` não vai para o git.

| Variável | Uso |
|---|---|
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | Django |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `DB_SSLMODE` | RDS. Sem `DB_HOST`, usa SQLite local |
| `AWS_REGION`, `S3_BUCKET`, `SNS_TOPIC_ARN`, `SQS_QUEUE_URL`, `DYNAMODB_TABLE`, `REDIS_URL` | AWS (ainda não lidas pelo código) |
