# Backend (API Django)

API REST em Django. Valida o pedido, grava no Postgres, envia o PDF ao MinIO, registra o log no DynamoDB, usa o cache Redis e publica o evento no RabbitMQ para o worker.

## Estrutura

```
backend/
├── manage.py
├── requirements.txt
├── .env.example          modelo das variáveis de ambiente
├── article_cloud/        configuração (settings, urls, wsgi) e helpers HTTP
├── accounts/             cadastro, login e token
└── articles/
    ├── models.py         Article, Author, Tag
    ├── views.py          rotas da API (só orquestram)
    ├── urls.py
    ├── migrations/       esquema e artigos de demonstração (0005)
    ├── services/         uma camada fina por serviço AWS
    │   ├── aws.py            clientes boto3
    │   ├── s3.py             PDF
    │   ├── dynamo_log.py     log das ações
    │   ├── cache.py          Redis
    │   └── messaging.py      RabbitMQ (publica o evento de novo artigo)
    ├── demo/             dados e gerador de PDFs da demonstração
    ├── management/       comando carregar_demo_pdfs
    └── tests/            unit/, integration/ e fixtures/
```

## Rotas

Autenticação por token: o login devolve um token assinado (válido por 7 dias, sem estado no servidor). Envie em `Authorization: Token <token>`. Todas as instâncias da API precisam da mesma `DJANGO_SECRET_KEY`.

| Método | Rota | Função | Login |
|---|---|---|---|
| GET | `/health/` | Health check do balanceador (não consulta banco nem AWS) | não |
| POST | `/auth/register/` | Cria usuário (`username`, `email`, `password`) | não |
| POST | `/auth/login/` | Devolve `{token, username}` | não |
| GET | `/articles/` | Lista os artigos | não |
| POST | `/articles/` | Cadastra um artigo (multipart com PDF). O dono é o usuário do token | sim |
| GET | `/articles/<id>/` | Detalhe | não |
| PUT | `/articles/<id>/` | Atualiza título, autores, área, tags e resumo (JSON). Só o dono | sim |
| DELETE | `/articles/<id>/` | Remove o artigo e o PDF. Só o dono | sim |
| POST | `/articles/<id>/reprocess/` | Reenvia ao worker um artigo em `ERRO`. Só o dono | sim |
| GET | `/articles/search/?q=` | Busca em título, autor, área e palavra-chave | não |
| GET | `/articles/<id>/download/` | `{download_url}`: URL pré-assinada do PDF (300 s) | não |

Exemplo (copie o `token` da resposta do login):

```
curl -X POST http://127.0.0.1:8000/auth/login/ -H "Content-Type: application/json" \
  -d '{"username": "teste", "password": "sua-senha"}'

curl -X POST http://127.0.0.1:8000/articles/ -H "Authorization: Token <token>" \
  -F title="Introdução à Nuvem" -F area="Computação" -F abstract="Resumo" \
  -F authors='["Ana", "Bruno"]' -F tags='["AWS", "Python"]' \
  -F file=@articles/tests/fixtures/pdfs/artigo_nuvem.pdf
```

`authors` e `tags` são listas em JSON dentro do campo do formulário. O PDF pode ter até 10 MB.

Erros vêm sempre como `{"erro": "..."}`:

| Código | Quando |
|---|---|
| 400 | Campo obrigatório ausente, JSON inválido, PDF ausente, senha fraca |
| 401 | Sem token, token inválido ou expirado, login errado |
| 403 | Alterar ou apagar o artigo de outro usuário |
| 404 | Artigo inexistente |
| 409 | Título ou usuário já cadastrado; reprocessar um artigo que não está em `ERRO` |
| 413 / 415 | PDF acima de 10 MB / arquivo que não é PDF |
| 502 | Falha ao falar com o S3 (o detalhe fica só no log) |
| 503 | Artigo salvo, mas o evento não foi publicado. A resposta traz `article_id` para reprocessar |

Toda resposta de artigo traz `id`, `title`, `authors`, `area`, `abstract`, `translated_abstract`, `processing_status`, `upload_datetime`, `user` e `tags`.

## Banco de dados

O modelo está no README da raiz. As migrations `0001` a `0004` criam o esquema. A `0005` carrega 12 artigos fictícios (dono `demo`) para demonstrar a busca; ela não roda nos testes e é desligada com `SEED_DEMO_DATA=0`.

```
python manage.py migrate
python manage.py carregar_demo_pdfs            # envia os PDFs de demonstração ao S3
python manage.py carregar_demo_pdfs --saida p  # ou só grava os PDFs na pasta p
python manage.py migrate articles 0004         # remove os artigos de demonstração
```

Nunca edite uma migration já aplicada no RDS. Mudou um model? Rode `makemigrations` e commite o arquivo novo.

## Testes

| Pasta | O que prova | Custo |
|---|---|---|
| `tests/unit/` | A lógica do código, com a AWS simulada (30 testes) | nenhum |
| `tests/integration/` | Que a AWS real está configurada como a aplicação espera | cobra; só com `RUN_AWS_INTEGRATION=1` |

```
python manage.py test                                                    # unitários
RUN_AWS_INTEGRATION=1 python manage.py test articles.tests.integration   # AWS real
```

`tests/fixtures/pdfs/` tem PDFs de vários cenários (ver `tests/fixtures/README.md`). Detalhes dos testes de integração em `tests/integration/README.md`.

## Variáveis de ambiente

Copie `.env.example` para `.env` (o `.env` não vai para o git).

| Variável | Uso |
|---|---|
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | Django. Com `DJANGO_DEBUG=False` a chave é obrigatória |
| `CORS_ALLOWED_ORIGINS` | Origens do front autorizadas, separadas por vírgula |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `DB_SSLMODE` | RDS. Sem `DB_HOST`, usa SQLite local |
| `AWS_REGION` | Região dos clientes boto3 |
| `S3_BUCKET` | Bucket dos PDFs |
| `DYNAMODB_TABLE` | Tabela de logs (padrão `logs_crud`) |
| `RABBITMQ_HOST`, `RABBITMQ_PORT` | Endereço do broker (no compose, `rabbitmq` e `5672`) |
| `RABBITMQ_DEFAULT_USER`, `RABBITMQ_DEFAULT_PASS` | Login do broker |
| `RABBITMQ_QUEUE` | Fila do evento de novo artigo (padrão `artigos.criados`) |
| `REDIS_URL` | Cache, formato `redis://<endpoint>:6379/0` |
| `SEED_DEMO_DATA`, `DEMO_USER_PASSWORD` | Artigos de demonstração e senha opcional do usuário `demo` |

Em produção (`DJANGO_DEBUG=False`) o Django não sobe sem `DJANGO_SECRET_KEY`, `MINIO_ENDPOINT_URL`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `DYNAMODB_TABLE`, `RABBITMQ_HOST`, `RABBITMQ_DEFAULT_USER` e `RABBITMQ_DEFAULT_PASS`. Na EC2 use a IAM Role (LabRole) e deixe as chaves AWS fora do `.env`.
