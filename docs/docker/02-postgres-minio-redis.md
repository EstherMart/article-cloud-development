# 2. Postgres, MinIO e Redis

[← 1. Docker Compose](01-compose.md) | [Índice](README.md) | [3. Dockerfiles →](03-dockerfiles.md)

O RabbitMQ tem página própria: [rabbitmq.md](rabbitmq.md).

## Postgres (substitui o RDS)

**Requisito:** banco relacional gerenciado pela equipe (1,5 pt: 0,5 container, 1,0 aplicação conectando e persistindo).

```yaml
postgres:
  image: postgres:16
  environment:
    POSTGRES_DB: ${POSTGRES_DB}
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  volumes:
    - postgres_data:/var/lib/postgresql/data
  healthcheck: pg_isready ...
```

- **Imagem oficial.** Na primeira subida, com o volume vazio, a imagem cria o banco, o usuário e a senha a partir das três variáveis `POSTGRES_*`. Nas seguintes, o volume já tem dados e as variáveis são ignoradas (trocar a senha no `.env` depois não muda a senha do banco).
- **Volume** `postgres_data`: os dados sobrevivem a `docker compose down`.
- **Conexão do backend** (`article_cloud/settings.py`): se `DB_HOST` está definido, usa `django.db.backends.postgresql` com `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST=postgres`, `DB_PORT`. Sem `DB_HOST`, cai em SQLite (só para rodar fora do Docker).
- **Conexão do worker** (`worker/worker.py`): `psycopg2` direto, mesmas variáveis, e faz `UPDATE` em `articles_article`. Usa `sslmode` de `DB_SSLMODE`, com padrão `require`. O Postgres do container **não tem TLS**, por isso o `.env` precisa de `DB_SSLMODE=disable`, senão o worker não conecta.
- **Tabelas:** vêm das migrations do Django (`python manage.py migrate`). A migration `0005` também cria artigos de demonstração (desligável com `SEED_DEMO_DATA=0`).
- **Evidência de que persiste:** `docker compose exec postgres psql -U <usuario> -d artigos -c "select id, title, processing_status from articles_article;"`.

Perguntas: *Por que o banco usa volume?* Sem ele, o container apagaria os dados ao ser recriado. *Por que a senha não está no compose?* Vem do `.env`, que não é versionado.

## MinIO (substitui o S3)

**Requisito:** armazenar os arquivos (1,5 pt: 0,5 container, 1,0 upload e download funcionando na aplicação).

MinIO é um servidor de armazenamento de objetos compatível com a API do S3. Por isso o código continua usando `boto3`; só muda o endereço e as chaves.

```yaml
minio:
  image: cgr.dev/chainguard/minio:latest
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: ${MINIO_ROOT_USER}
    MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
  ports: ["9000:9000", "9001:9001"]
  volumes: [minio_data:/data]
```

- `server /data` sobe o servidor guardando os objetos em `/data` (o volume). `--console-address ":9001"` fixa a porta do console web; a API fica na 9000.
- A imagem é da Chainguard (`cgr.dev/chainguard/minio`), não a `minio/minio`. A tag é `latest`, **sem versão fixa**: uma subida futura pode trazer outra versão.
- As credenciais de administrador (`MINIO_ROOT_USER/PASSWORD`) são usadas também como chaves de acesso do `boto3` no backend e no worker. É simples, mas é a conta root; em produção criaria-se um usuário de serviço com política restrita.

### Código: `backend/articles/services/aws.py` e `minIO.py`

| Ponto | Como está | Por quê |
|---|---|---|
| `endpoint_url` | `MINIO_ENDPOINT_URL` (`http://minio:9000`) | Aponta o `boto3` para o MinIO em vez da AWS |
| `addressing_style: path` | `http://minio:9000/artigos/...` | O estilo virtual-host (`artigos.minio:9000`) exigiria DNS por bucket, que a rede do Docker não tem |
| `signature_version: s3v4` | Assinatura v4 | Necessária para URLs pré-assinadas |
| Bucket | `MINIO_BUCKET` (`artigos`), criado por `create_bucket()` no primeiro upload; ignora `BucketAlreadyOwnedByYou` | Dispensa criar o bucket à mão |
| Chave do objeto | `artigos/{id}.pdf` | Igual à do trabalho 1 |
| Upload | `upload_fileobj` com `ContentType: application/pdf` | Envia em partes, sem carregar tudo na memória |
| Cliente | `lru_cache` por endpoint | Um cliente por endpoint, reaproveitado |

### Dois endereços: interno e público

Esta é a parte mais cobrada de entender.

| Variável | Valor no compose | Quem usa |
|---|---|---|
| `MINIO_ENDPOINT_URL` | `http://minio:9000` | Backend e worker, **dentro** da rede do Docker |
| `MINIO_PUBLIC_ENDPOINT_URL` | `http://localhost:9000` | O **navegador**, que está fora da rede |

O download não passa pela API: o backend devolve uma URL pré-assinada (`GET /articles/<id>/download/`, válida por 300 s) e o navegador baixa direto do MinIO. Se a URL fosse gerada com `http://minio:9000`, o navegador não resolveria o nome `minio`. Por isso `presigned_url()` usa `minio_client(public=True)`: a assinatura já nasce com o host público, porque a assinatura v4 inclui o host e trocar o endereço depois invalidaria a URL (o `url.replace(interno, publico)` que existe no fim de `presigned_url()` é, na prática, um no-op: a URL já sai com o endereço público, então não há o que trocar).

**Consequência para uma VM na AWS:** `MINIO_PUBLIC_ENDPOINT_URL` precisa ser o endereço *alcançável pelo navegador de quem avalia* (IP público da VM, porta 9000 liberada no Security Group), não `localhost`.

### Evidência
- Console `http://localhost:9001`: bucket `artigos` com objetos `artigos/<id>.pdf`.
- Pela aplicação: criar artigo com PDF e depois clicar em baixar.

## Redis (substitui o ElastiCache)

Não é exigido pela spec, mas foi mantido porque o cache já existia.

```yaml
redis:
  image: redis:7-alpine
  ports: ["6379:6379"]
```

- Padrão **cache-aside** (`backend/articles/services/cache.py`): lê do Redis; se não tem (miss), consulta o Postgres, grava com TTL de 300 s e devolve. Chaves: `artigo:{id}`, `artigos:recentes`, `busca:{termos}`. Só metadados, nunca o PDF.
- Conexão por `REDIS_URL=redis://redis:6379/0`, com timeout de 2 s.
- **Falha não derruba a API:** toda exceção do Redis é capturada e registrada; sem cache a leitura vai ao banco.
- **Invalidação:** a API apaga as chaves ao criar, editar e excluir; o worker apaga as mesmas ao terminar a tradução, para a tela mostrar `PROCESSADO`.
- Não tem volume nem healthcheck, e nenhum serviço declara `depends_on` dele. Funciona porque o cache é opcional.

Pergunta provável: *O que acontece se o Redis cair?* A API continua e fica mais lenta, porque todas as leituras vão ao Postgres.

[← 1. Docker Compose](01-compose.md) | [Índice](README.md) | [3. Dockerfiles →](03-dockerfiles.md)
