# Backend (API Django)

API REST em Django. Responsável por validar, gravar no RDS, enviar o PDF ao S3, logar no DynamoDB, usar o cache Redis e publicar no SNS.

## Estrutura

```
backend/
├── manage.py
├── requirements.txt
├── .env.example          modelo das variáveis de ambiente
├── article_cloud/        configuração do projeto (settings, urls, wsgi, http.py com helpers)
├── accounts/             cadastro, login e token
└── articles/             app principal
    ├── models.py         Article, Tag, Author
    ├── migrations/       0001 a 0004 (ver Migrations)
    ├── views.py          rotas da API (só orquestram)
    ├── urls.py           mapa de rotas
    ├── tests/            unit/ (sem AWS) e integration/ (AWS real, desligado por padrão)
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

Autenticação por token: o login devolve um token assinado (`django.core.signing`, validade de 7 dias, sem estado no servidor). Envie em `Authorization: Token <token>`. Todas as instâncias da API precisam usar a mesma `DJANGO_SECRET_KEY`.

| Método | Rota | Função | Autenticação |
|---|---|---|---|
| POST | `/auth/register/` | Cria usuário (`username`, `email`, `password`) | não |
| POST | `/auth/login/` | Devolve `{token, username}` | não |
| GET | `/articles/` | Lista artigos | não |
| POST | `/articles/` | Cadastra artigo (multipart com PDF). O dono é o usuário do token | sim |
| GET | `/articles/<id>/` | Detalhe | não |
| PUT | `/articles/<id>/` | Atualiza título, autores, área, tags e resumo (JSON). Só o dono | sim |
| DELETE | `/articles/<id>/` | Remove o artigo e o PDF do S3. Só o dono | sim |
| GET | `/articles/search/?q=` | Busca em título, autor, área e tag | não |
| GET | `/articles/<id>/download/` | URL pré-assinada do PDF | não |

`/articles/search/` fica antes de `/articles/<id>/` no `urls.py` para a busca não ser confundida com um id.

Exemplo: login e cadastro de artigo (copie o `token` da resposta do login):

```
curl -X POST http://127.0.0.1:8000/auth/login/ -H "Content-Type: application/json" \
  -d '{"username": "teste", "password": "sua-senha"}'

curl -X POST http://127.0.0.1:8000/articles/ -H "Authorization: Token <token>" \
  -F title="Introdução à Nuvem" -F area="Computação" -F abstract="Resumo" \
  -F authors='["Ana", "Bruno"]' -F tags='["AWS", "Python"]' \
  -F file=@articles/tests/fixtures/pdfs/artigo_nuvem.pdf
```

`authors` e `tags` são listas em JSON dentro do campo do formulário.

Respostas de erro (sempre `{"erro": "..."}`):

| Código | Quando |
|---|---|
| 400 | Campo obrigatório ausente, JSON inválido, PDF ausente, senha fraca |
| 401 | Sem token, token inválido ou expirado, login errado |
| 403 | Alterar ou apagar artigo de outro usuário |
| 404 | Artigo inexistente |
| 409 | Título ou nome de usuário já cadastrado |

Toda resposta de artigo traz `id`, `title`, `authors`, `area`, `abstract`, `translated_abstract`, `processing_status`, `upload_datetime`, `user` e `tags`.

CORS: as origens do front liberadas ficam em `CORS_ALLOWED_ORIGINS` (padrão `http://127.0.0.1:8080` e `http://localhost:8080`).

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

Dois grupos, com responsabilidades diferentes:

| Pasta | O que prova | Rede e custo | Quando roda |
|---|---|---|---|
| `tests/unit/` | A lógica do nosso código (SQLite em memória, AWS simulada) | Nenhum | Sempre |
| `tests/integration/` | Que a AWS real funciona: rede, permissões, nomes dos recursos | Cobra, precisa de credenciais | Só com `RUN_AWS_INTEGRATION=1` |

```
python manage.py test                              # unitários (os 6 grupos de integração aparecem como skipped)
python manage.py test articles.tests.unit.test_models   # um arquivo
RUN_AWS_INTEGRATION=1 python manage.py test articles.tests.integration   # AWS real (desligado por padrão)
```

### Unitários (`tests/unit/`)

| Arquivo | Responsabilidade |
|---|---|
| `base.py` | `ApiTestCase`: cria o usuário e oferece helpers (`post_article`, `create_article`, `send`) |
| `test_models.py` | Regras do modelo: status padrão, unicidade, N:N, `CASCADE` |
| `test_article_create.py` | `POST /articles/`: sucesso e erros 400 e 404 |
| `test_article_read.py` | `GET /articles/` e `GET /articles/<id>/` |
| `test_article_update_delete.py` | `PUT` e `DELETE` |
| `test_article_search.py` | `GET /articles/search/` |
| `test_aws_clients.py` | Fábrica boto3 (`services/aws.py`): cache, região, timeouts, retries, Signature v4. Não abre conexão |

### Integração (`tests/integration/`)

Os testes estão escritos e desligados (`RUN_AWS_INTEGRATION=1` liga). Cada arquivo se pula sozinho se faltar variável do `.env`. Variáveis, regras e o que cada um prova estão em `tests/integration/README.md`.

| Arquivo | Serviço |
|---|---|
| `base.py` | Liga e desliga os testes (`RUN_AWS_INTEGRATION`) e pula o que não tem recurso |
| `test_rds.py` | RDS |
| `test_s3.py` | S3 |
| `test_dynamodb.py` | DynamoDB |
| `test_sns_sqs.py` | SNS, SQS e DLQ |
| `test_redis.py` | ElastiCache (só da EC2) |
| `test_pipeline_e2e.py` | Fluxo completo |

`tests/fixtures/pdfs/` tem PDFs de exemplo (com texto, sem texto e inválido) para os testes de upload e do worker. Ver `tests/fixtures/README.md`.

Ao implementar um serviço, escreva primeiro o teste unitário com o cliente simulado (`unittest.mock`) em `unit/test_<servico>.py`. Depois descomente o teste de integração do mesmo serviço.

## Variáveis de ambiente

Copie `.env.example` para `.env`. O `.env` não vai para o git.

| Variável | Uso |
|---|---|
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | Django |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `DB_SSLMODE` | RDS. Sem `DB_HOST`, usa SQLite local |
| `AWS_REGION` | Região usada pelos clientes boto3 |
| `S3_BUCKET` | Bucket S3 usado no upload e no download dos PDFs |
| `SNS_TOPIC_ARN` | Tópico SNS para publicar eventos de novos artigos |
| `SQS_QUEUE_URL` | Fila que o worker consome |
| `REDIS_URL` | Endpoint Redis usado pelo cache da API |
| `DYNAMODB_TABLE` | Nome da tabela de logs (padrão `logs_crud`) |

`REDIS_URL` usa o formato `redis://<endpoint-do-elasticache>:6379/0`. Na EC2 use a IAM Role (LabRole) e deixe as chaves AWS fora do `.env`.
