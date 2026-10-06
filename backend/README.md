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
    ├── views.py          rotas da API
    └── urls.py           mapa de rotas
```

Quando o código crescer, a integração com a AWS entra em `articles/services/`, um módulo por serviço (`s3.py`, `dynamo_log.py`, `cache.py`, `sns.py`). As views só orquestram. Assim cada branch `feat/...` mexe em arquivos diferentes e há menos conflito.

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

## Modelo de dados (RDS)

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

Log no DynamoDB (`logs_crud`): tipo da ação, dados manipulados e hora. A spec exige os três. O esboço do grupo tinha só Status e Mensagem, então falta decidir a chave da tabela.

## Variáveis de ambiente

Copie `.env.example` para `.env`. O `.env` não vai para o git.

| Variável | Uso |
|---|---|
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | Django |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `DB_SSLMODE` | RDS. Sem `DB_HOST`, usa SQLite local |
| `AWS_REGION`, `S3_BUCKET`, `SNS_TOPIC_ARN`, `SQS_QUEUE_URL`, `DYNAMODB_TABLE`, `REDIS_URL` | AWS (ainda não lidas pelo código) |

Na EC2 não há chaves de acesso: o boto3 usa a IAM Role (LabRole).

## Rodar

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
set -a; source .env; set +a
python manage.py makemigrations && python manage.py migrate
python manage.py runserver
```

O repositório ainda não tem migrations commitadas. Quem rodar `makemigrations` primeiro deve commitar o resultado.

## Banco RDS

1. Criar o banco: conecte com `psql` e rode `CREATE DATABASE academichub;`.
2. Preencher `DB_HOST` (endpoint do RDS), `DB_NAME`, `DB_USER` e `DB_PASSWORD` no `.env`.
3. O Security Group do RDS deve aceitar a porta 5432 só das instâncias da aplicação (e do seu IP, durante o desenvolvimento).
4. Para `sslmode=verify-full`, baixe o `global-bundle.pem` da AWS. O padrão do projeto é `require`.

Passo a passo completo em `../docs/aws-setup.md`.

## Regras para implementar o CRUD

Ordem do cadastro (`POST /articles/`):

1. Validar: só `application/pdf`, tamanho máximo, título, ao menos um autor e resumo.
2. Gravar no RDS com status PENDENTE para obter o id.
3. Enviar o PDF ao S3 com o id na chave, e atualizar `s3_key`. Se o envio falhar, apagar o registro ou marcar ERRO.
4. Registrar o CREATE no DynamoDB.
5. Publicar no SNS e responder sem esperar a tradução.

Todo CREATE, UPDATE e DELETE invalida `artigo:{id}`, `artigos:recentes` e `busca:*` no Redis. O TTL (5 a 10 minutos) é a rede de segurança.
