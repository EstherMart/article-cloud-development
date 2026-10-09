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
    ├── migrations/       0001 a 0004 (ver Migrations)
    ├── views.py          rotas da API (só orquestram)
    ├── urls.py           mapa de rotas
    ├── tests/            testes unitários, um arquivo por responsabilidade
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
| POST | `/articles/` | Cadastra artigo | implementado em JSON, sem PDF, S3, DynamoDB e SNS |
| GET | `/articles/<id>/` | Detalhe | implementado |
| PUT | `/articles/<id>/` | Atualiza título, autores e área | implementado |
| DELETE | `/articles/<id>/` | Remove | implementado (não apaga o PDF do S3 ainda) |
| GET | `/articles/search/?q=` | Busca em título, autor, área e tag | implementado |
| GET | `/articles/<id>/download/` | URL pré-assinada do PDF | stub |

`/articles/search/` fica antes de `/articles/<id>/` no `urls.py` para a busca não ser confundida com um id.

Exemplo de cadastro (o usuário precisa existir; sem login, o POST recebe o `username`):

```
curl -X POST http://127.0.0.1:8000/articles/ -H "Content-Type: application/json" -d '{
  "title": "Introdução à Nuvem", "authors": ["Ana", "Bruno"],
  "area": "Computação", "user": "teste", "tags": ["AWS", "Python"]}'
```

Crie o usuário com `python manage.py createsuperuser` ou pelo `manage.py shell`. O arquivo `articles/guia_p_testar.txt` traz o mesmo roteiro para Windows.

## Modelo de dados (RDS)

Diagrama e decisões em `../README.md`. Resumo das tabelas:

`Article`:

| Campo | Tipo | Observação |
|---|---|---|
| `id` | BigAutoField, PK | |
| `title` | texto (255), único | |
| `area` | texto (255) | |
| `abstract` | texto | resumo digitado no cadastro (a API ainda não recebe) |
| `translated_abstract` | texto | preenchido pelo worker |
| `s3_key` | texto (512) | chave do PDF, preenchida após salvar o registro |
| `processing_status` | PENDENTE, PROCESSANDO, PROCESSADO, ERRO | padrão PENDENTE |
| `upload_datetime` | data e hora | automático |
| `user` | FK para `User` | `CASCADE` |
| `authors` | M2M com `Author` | |
| `tags` | M2M com `Tag` | |

`Author`: `id`, `name`. `Tag`: `id`, `name` (único).

## Migrations

| Arquivo | O que faz |
|---|---|
| `0001_initial` | Cria `Author`, `Tag` e `Article` |
| `0002_remove_article_author_article_authors` | Troca o campo `author` (texto) por `authors` (M2M) |
| `0003_alter_article_id_...` | Passa os ids para `BigAutoField` (Django 6.1) |
| `0004_article_abstract_article_s3_key_and_more` | Adiciona `abstract`, `translated_abstract` e `s3_key` |

Nunca edite uma migration já aplicada no RDS. Mudou um model? Rode `python manage.py makemigrations` e commite o arquivo novo. O comando `python manage.py makemigrations --check` deve dizer "No changes detected".

## Testes

```
python manage.py test                       # todos
python manage.py test articles.tests.test_models   # um arquivo
```

Os testes usam SQLite em memória e não falam com a AWS. Cada arquivo cobre uma responsabilidade:

| Arquivo | Responsabilidade |
|---|---|
| `tests/base.py` | `ApiTestCase`: cria o usuário e oferece helpers (`post_article`, `create_article`, `send`) |
| `tests/test_models.py` | Regras do modelo: status padrão, unicidade, N:N, `CASCADE` |
| `tests/test_article_create.py` | `POST /articles/`: sucesso e erros 400 e 404 |
| `tests/test_article_read.py` | `GET /articles/` e `GET /articles/<id>/` |
| `tests/test_article_update_delete.py` | `PUT` e `DELETE` |
| `tests/test_article_search.py` | `GET /articles/search/` |

Quando implementar um serviço AWS, crie `tests/test_<servico>.py` com o cliente simulado (`unittest.mock`), para os testes seguirem rodando sem custo e sem rede.

## Variáveis de ambiente

Copie `.env.example` para `.env`. O `.env` não vai para o git.

| Variável | Uso |
|---|---|
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | Django |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `DB_SSLMODE` | RDS. Sem `DB_HOST`, usa SQLite local |
| `AWS_REGION`, `S3_BUCKET`, `SNS_TOPIC_ARN`, `SQS_QUEUE_URL`, `DYNAMODB_TABLE`, `REDIS_URL` | AWS (ainda não lidas pelo código; `DB_SSLMODE` já vale) |

`REDIS_URL` usa o formato `redis://<endpoint-do-elasticache>:6379/0`. Na EC2 use a IAM Role (LabRole) e deixe as chaves AWS fora do `.env`.
