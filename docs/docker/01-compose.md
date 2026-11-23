# 1. Docker Compose

[Índice](README.md) | [2. Postgres, MinIO e Redis →](02-postgres-minio-redis.md)

## O que é

Docker **imagem** é o pacote (sistema + dependências + código). **Container** é a imagem em execução, isolado. O **Docker Compose** descreve vários containers num único arquivo (`docker-compose.yml`) e os sobe juntos, com rede, volumes e ordem de início. É a resposta ao requisito 7 da spec: "todos os serviços sobem via um único comando" (`docker compose up`).

## Os sete serviços

| Serviço | Origem | Container | Portas (host:container) | Volume | Healthcheck |
|---|---|---|---|---|---|
| `backend` | `build: ./backend` | `artigos-backend` | 8000:8000 | (nenhum) | não |
| `frontend` | `build: ./frontend` | `artigos-frontend` | 8080:80 | (nenhum) | não |
| `postgres` | `postgres:16` | `artigos-postgres` | 5432:5432 | `postgres_data` | `pg_isready` |
| `minio` | `cgr.dev/chainguard/minio:latest` | `artigos-minio` | 9000:9000 (API), 9001:9001 (console) | `minio_data` | não |
| `rabbitmq` | `rabbitmq:3-management` | `artigos-rabbitmq` | 5672:5672 (AMQP), 15672:15672 (painel) | `rabbitmq_data` | `rabbitmq-diagnostics ping` |
| `worker` | `build: ./worker` | `artigos-worker` | (nenhuma: só consome) | (nenhum) | não |
| `redis` | `redis:7-alpine` | `artigos-redis` | 6379:6379 | (nenhum) | não |

Três serviços usam `build` (têm Dockerfile próprio: backend, worker e frontend). Os outros quatro usam imagem pronta (`image`), como a spec pede nos itens 4, 5 e 6.

## Rede

```yaml
networks:
  artigos-network:
    driver: bridge
```

Todos os serviços entram em `artigos-network`, uma rede *bridge* criada pelo Compose. Duas consequências:

- **DNS por nome de serviço.** Dentro da rede, o backend acessa o banco em `postgres:5432`, o MinIO em `minio:9000`, o broker em `rabbitmq:5672`. É por isso que o `.env` usa `DB_HOST=postgres`, `MINIO_ENDPOINT_URL=http://minio:9000`, `RABBITMQ_HOST=rabbitmq`, `REDIS_URL=redis://redis:6379/0`. `localhost` dentro de um container é o próprio container, não os outros.
- **`ports` serve só para o host.** O mapeamento `8080:80` abre a porta do *seu computador* para o container. A comunicação entre containers não usa `ports`: ela usa a rede e a porta interna.

Há uma única rede. Todos se enxergam. Separar em duas (uma "web" com frontend e backend, uma "dados" com backend, worker e os serviços) seria mais restritivo, mas não foi feito (ver [limitações](07-estudo-arguicao.md#limitações-conhecidas)).

## Volumes

```yaml
volumes:
  postgres_data:
  minio_data:
  rabbitmq_data:
```

Volumes nomeados guardam os dados fora do ciclo de vida do container: `docker compose down` remove containers, mas os volumes ficam e o banco, os PDFs e as filas duráveis sobrevivem. Só `docker compose down -v` apaga.

| Volume | Montado em | O que guarda |
|---|---|---|
| `postgres_data` | `/var/lib/postgresql/data` | Tabelas do Postgres |
| `minio_data` | `/data` | Buckets e objetos (os PDFs) |
| `rabbitmq_data` | `/var/lib/rabbitmq` | Filas duráveis e mensagens persistentes |

O Redis não tem volume de propósito: é cache, perder o conteúdo só custa uma nova consulta ao banco.

## Variáveis de ambiente: o `.env`

Há dois mecanismos no compose:

| Mecanismo | Quem usa | Como funciona |
|---|---|---|
| `env_file: .env` | `backend` e `worker` | Todas as variáveis do arquivo entram no container |
| `environment: X: ${X}` | `postgres`, `minio`, `rabbitmq` | O Compose lê o `.env` **ao interpretar o YAML** e injeta só as variáveis listadas |

O `.env` não vai para o Git (está no `.gitignore`); o `.env.example` é o modelo, com os valores sensíveis em branco. Os mesmos valores servem aos dois lados de cada serviço: `POSTGRES_USER/PASSWORD` criam o usuário do banco e `DB_USER/DB_PASSWORD` fazem o backend entrar com ele; `MINIO_ROOT_USER/PASSWORD` criam o admin do MinIO e o backend usa os mesmos como chave de acesso; `RABBITMQ_DEFAULT_USER/PASS` criam o login do broker e os dois clientes usam o mesmo.

## `depends_on` e healthcheck

`depends_on` define a **ordem de início**. Sozinho, só espera o container *iniciar*, não estar *pronto*. Com `condition: service_healthy`, espera o healthcheck passar.

```yaml
backend:
  depends_on:
    postgres: {condition: service_healthy}
    rabbitmq: {condition: service_healthy}
worker:
  depends_on:
    rabbitmq: {condition: service_healthy}
    minio:    {condition: service_started}
frontend:
  depends_on: [backend]
```

Healthchecks existentes:

| Serviço | Teste | Por quê |
|---|---|---|
| `postgres` | `pg_isready -U admin -d artigos` a cada 5 s, 5 tentativas | O Postgres demora a aceitar conexão. Sem isso o Django tentaria conectar e cairia |
| `rabbitmq` | `rabbitmq-diagnostics -q ping` a cada 10 s | O broker leva alguns segundos para subir; o `pika` falharia ao conectar antes |

O MinIO não tem healthcheck e o worker só espera `service_started` dele. Isso funciona porque o bucket é criado sob demanda pelo backend (`create_bucket()` no primeiro upload) e o worker só acessa o MinIO ao processar uma mensagem, bem depois da subida. Um healthcheck no MinIO seria mais rigoroso (ver [limitações](07-estudo-arguicao.md#limitações-conhecidas)).

Mesmo com tudo isso, o worker e o backend têm **reconexão por conta própria**: o worker captura `AMQPError`/`OSError` e tenta de novo a cada 5 s (`main()` em `worker/worker.py`); o backend abre uma conexão nova a cada publicação. A ordem do compose reduz erros no início, não substitui a resiliência.

## Portas expostas no host

| Porta | Serviço | Para quê |
|---|---|---|
| 8080 | frontend | Telas (entrada do usuário) |
| 8000 | backend | API direta (testes com `curl`, Postman) |
| 9000 | minio | API S3. **Precisa estar no host** porque o navegador baixa o PDF direto dela |
| 9001 | minio | Console web |
| 15672 | rabbitmq | Painel de gerenciamento |
| 5672 | rabbitmq | AMQP (só necessário para ferramentas de fora) |
| 5432 | postgres | Para `psql` do host (só desenvolvimento) |
| 6379 | redis | Para `redis-cli` do host (só desenvolvimento) |

Entre containers nada disso é necessário. 5432, 5672 e 6379 estão abertas por conveniência de estudo; numa VM pública convém removê-las.

## Perguntas prováveis

1. **Qual a diferença entre imagem e container?** Imagem é o modelo imutável; container é uma instância em execução dela.
2. **Por que `localhost` não funciona entre containers?** Cada container tem a própria rede; `localhost` é ele mesmo. Usa-se o nome do serviço, resolvido pelo DNS interno da rede do Compose.
3. **`depends_on` garante que o banco está pronto?** Não, só a ordem. Com `condition: service_healthy` e um healthcheck, sim.
4. **O que acontece com os dados no `docker compose down`? E no `down -v`?** `down` mantém os volumes. `down -v` apaga.
5. **Por que o `.env` fica fora do Git?** Tem senhas e chave do Gemini. O repositório tem só o `.env.example`.
6. **Qual a diferença entre `env_file` e `environment`?** `env_file` injeta o arquivo todo no container; `environment` lista variáveis específicas (com `${}` lidas do `.env` na hora de montar o YAML).
7. **Por que expor a porta 9000 do MinIO no host?** Porque a URL pré-assinada é aberta pelo navegador, que está fora da rede do Docker.

[Índice](README.md) | [2. Postgres, MinIO e Redis →](02-postgres-minio-redis.md)
