# 3. Dockerfiles: backend, worker e frontend

[← 2. Postgres, MinIO e Redis](02-postgres-minio-redis.md) | [Índice](README.md) | [4. Frontend e Nginx →](04-frontend-nginx.md)

**Requisito:** Dockerfile correto para backend, worker e frontend (1,5 pt). Um `Dockerfile` é a receita de uma imagem: cada instrução cria uma camada, e o Docker reaproveita do cache as camadas que não mudaram.

## Backend (`backend/Dockerfile`)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

| Instrução | O que faz | Por quê |
|---|---|---|
| `FROM python:3.12-slim` | Base Debian enxuta com Python 3.12 | Menor que a imagem completa; o projeto exige 3.12 |
| `WORKDIR /app` | Pasta de trabalho dentro da imagem | Os comandos seguintes rodam ali |
| `PYTHONDONTWRITEBYTECODE=1` | Não gera `.pyc` | Imagem mais limpa |
| `PYTHONUNBUFFERED=1` | Logs saem na hora, sem buffer | `docker compose logs` mostra em tempo real |
| `apt-get install gcc libpq-dev` | Compilador e cabeçalhos do Postgres | Só seriam necessários para compilar o `psycopg2`. Como o `requirements.txt` usa `psycopg2-binary`, **não são necessários** e podem ser removidos |
| `rm -rf /var/lib/apt/lists/*` | Apaga o índice do apt | Evita guardá-lo numa camada |
| `COPY requirements.txt` antes de `COPY . .` | Copia só a lista de dependências primeiro | **Cache de camadas:** se só o código mudou, o `pip install` não roda de novo |
| `--no-cache-dir` | pip não guarda cache | Imagem menor |
| `COPY . .` | Copia o código | Respeita o `.dockerignore` (o backend **não tem**; ver limitações) |
| `EXPOSE 8000` | Documenta a porta | Só documentação; quem publica é o `ports:` do compose |
| `CMD runserver 0.0.0.0:8000` | Comando padrão | `0.0.0.0` é obrigatório: em `127.0.0.1` só o próprio container alcançaria |

Pontos de arguição:
- **`runserver` é o servidor de desenvolvimento do Django.** `gunicorn` já está no `requirements.txt` mas não é usado; para produção o comando seria `gunicorn article_cloud.wsgi:application --bind 0.0.0.0:8000`.
- **A imagem não roda `migrate`.** As tabelas são criadas por `docker compose exec backend python manage.py migrate` (o pipeline faz isso). Detalhes em [limitações](07-estudo-arguicao.md#limitações-conhecidas).
- **A imagem roda como root** (não há `USER`).
- **A configuração não está na imagem.** O `.env` não deve entrar na imagem; o compose o injeta em tempo de execução (`env_file`). A mesma imagem serve a qualquer ambiente.

## Worker (`worker/Dockerfile`)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "worker.py"]
```

- Mesma receita, mais curta: não há porta (o worker não recebe requisições, **busca** mensagens do RabbitMQ), nem `EXPOSE`, nem dependência de sistema.
- **Imagem separada da API.** O worker não importa Django; tem o próprio `requirements.txt` (`boto3`, `psycopg2-binary`, `redis`, `pypdf`, `google-genai`, `pika<2`) e atualiza o banco com SQL direto. Isso permite escalar, atualizar e reiniciar cada um sem afetar o outro.
- **Contexto de build é `./worker`** (`build.context` no compose). Por isso a pasta `worker/` precisa ser autossuficiente: o código não pode depender de arquivos de `backend/`. É também o motivo de a topologia da fila estar duplicada nos dois lados ([rabbitmq.md](rabbitmq.md)).
- O código usa `tenacity` (retry da chamada ao Gemini) sem declará-lo no `requirements.txt`; ele chega como dependência do `google-genai`. Convém declarar explicitamente.
- `pika<2`: o `BlockingConnection` está deprecado na versão 2.

## Frontend (`frontend/Dockerfile`)

```dockerfile
FROM nginx:alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY *.html /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/
EXPOSE 80
```

- **Não há build do front** (HTML, CSS e JS puros): a imagem só empacota os arquivos num Nginx.
- Troca a configuração padrão do Nginx pela do projeto (explicada em [04](04-frontend-nginx.md)).
- `nginx:alpine` é pequena (Alpine Linux). A imagem inicia com o comando padrão do Nginx, por isso não há `CMD`.
- O `.dockerignore` do front exclui `Dockerfile`, `.dockerignore`, `.git` e `README.md`.

## Comparação

| | backend | worker | frontend |
|---|---|---|---|
| Base | `python:3.12-slim` | `python:3.12-slim` | `nginx:alpine` |
| Porta | 8000 | nenhuma | 80 |
| Processo | `runserver` | `worker.py` (loop de consumo) | Nginx |
| Dependências | Django, psycopg2-binary, boto3, redis, django-cors-headers, gunicorn, pika | boto3, psycopg2-binary, redis, pypdf, google-genai, pika | nenhuma |
| `.dockerignore` | não tem | não tem | tem |

## Comandos

```
docker compose build                # gera as três imagens
docker compose build backend        # só uma
docker compose build --no-cache     # ignora o cache de camadas
docker images                       # lista as imagens geradas
```

## Perguntas prováveis

1. **Por que copiar o `requirements.txt` antes do código?** Para o Docker reaproveitar a camada do `pip install` quando só o código muda.
2. **O que é `EXPOSE`?** Documentação da porta. Quem abre a porta para o host é o `ports:` do compose.
3. **Por que `0.0.0.0` no `runserver`?** Em `127.0.0.1` o servidor só aceitaria conexões do próprio container.
4. **Por que o worker é uma imagem à parte?** Tem outro papel, outras dependências e escala separado da API.
5. **Por que `runserver` e não `gunicorn`?** O `runserver` é de desenvolvimento. O `gunicorn` está no `requirements.txt` e seria o recomendado em produção.
6. **O que é uma imagem multi-stage?** Um Dockerfile com mais de um `FROM`, em que só o resultado final vai para a imagem. Não é usado aqui, mas serviria para compilar dependências e levar só o necessário.

[← 2. Postgres, MinIO e Redis](02-postgres-minio-redis.md) | [Índice](README.md) | [4. Frontend e Nginx →](04-frontend-nginx.md)
