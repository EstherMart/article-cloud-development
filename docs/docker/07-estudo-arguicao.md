# 7. Estudo para a arguição

[← 6. CI e deploy](06-ci-deploy.md) | [Índice](README.md)

## Mapa da spec para o código

| Requisito da spec | Pontos | Onde está | Estado |
|---|---|---|---|
| MinIO: container + upload/download | 1,5 | `docker-compose.yml` (`minio`), `backend/articles/services/minIO.py` | Implementado |
| NoSQL: armazenamento e consulta | 1,0 | `backend/articles/services/dynamo_log.py` | Grava. **Não há consulta na aplicação** |
| Postgres: container + persistência | 1,5 | `docker-compose.yml` (`postgres`), `settings.py` | Implementado |
| RabbitMQ: container + produção e consumo | 1,5 | `messaging.py`, `worker/worker.py`, [rabbitmq.md](rabbitmq.md) | Implementado |
| Dockerfiles de backend, worker e frontend | 1,5 | `backend/`, `worker/`, `frontend/` | Implementado (com ressalvas) |
| Compose: um comando + redes e dependências | 1,5 | `docker-compose.yml` | Implementado (com ressalvas) |
| README: instruções + prints | 1,5 | `README.md` | **Pendente** (ver abaixo) |
| Extra: Kubernetes (Deployment, NodePort, ClusterIP, secrets) | +1,0 | (não existe) | Não feito |
| Apresentação: slides, figuras, diagramas | 0 a -3 | fora do repositório | Ver o diagrama em [README.md](README.md) |

## Limitações conhecidas

Esta seção é a lista honesta do que falta ou é frágil. Quem for arguido deve saber dizer cada item antes que o professor perceba.

### Pendências que custam pontos

1. **O README raiz ainda descreve o trabalho 1.** Não há nenhuma instrução de `docker compose up`; a seção "Como rodar localmente" usa `venv`, SQLite e `python -m http.server`; a tabela de arquitetura, `img/arquitetura.svg` e "Problemas comuns" falam de EC2, RDS, S3, SNS e SQS. A seção de uso e o diagrama precisam refletir o compose. Vale 1,5 pt (1,0 instruções, 0,5 prints). Hoje só há links para esta pasta.
2. **Não há prints nem evidências no repositório.** `img/` só tem os diagramas da AWS. Prints sugeridos (criar uma pasta, por exemplo `docs/evidencias/`, e referenciar no README):
   - `docker compose ps` com os sete serviços e o `healthy` do Postgres e do RabbitMQ;
   - console do MinIO (`:9001`) com o bucket `artigos` e um `artigos/<id>.pdf`;
   - painel do RabbitMQ (`:15672`) na aba Queues, com `artigos.criados` e `artigos.criados.dlq`;
   - `psql` com `select id, title, processing_status from articles_article;`;
   - DynamoDB no console da AWS com itens `CREATE`;
   - telas: artigo recém-criado `PENDENTE`, depois `PROCESSADO` com a tradução, e o PDF baixado;
   - `docker compose logs worker` mostrando "processado e mensagem confirmada".
3. **`docker compose up` sozinho não cria as tabelas.** O `CMD` do backend é só `runserver`; o `migrate` só roda no pipeline (`deploy.yml`) ou à mão. Num clone novo, o backend sobe sem tabelas. A spec pontua "todos os serviços sobem via um único comando" (0,75). Correção possível: um entrypoint ou `command: sh -c "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"` no compose.
4. **Consulta no DynamoDB.** A spec fala em "armazenamento e consulta". Só há `put_item`. Uma rota simples como `GET /articles/<id>/logs/` (query por `article_id`) fecharia o requisito e daria o que mostrar na apresentação.
5. **Credenciais AWS do DynamoDB no container não estão documentadas nem no `.env.example`.** Ver [05](05-dynamodb-e-credenciais.md). Como `log_action` engole as exceções, o log pode estar falhando sem ninguém ver. A verificação é: `docker compose logs backend | grep "gravar o log"` e conferir a tabela no console. Em EC2, o limite de saltos do IMDSv2 precisa ser pelo menos 2 se for usar a role.

### Compose: dependências, rede e robustez

6. **Healthcheck do Postgres com valores fixos.** `pg_isready -U admin -d artigos` ignora `POSTGRES_USER` e `POSTGRES_DB`. Funciona só enquanto o usuário for `admin`. O correto é `pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}` (o `$$` impede o Compose de interpolar).
7. **`depends_on` incompleto.** O backend usa MinIO e Redis e não depende deles; o worker usa Postgres e Redis e depende só de RabbitMQ e MinIO; o frontend depende do backend só por `service_started`. Funciona hoje porque há reconexão e porque as conexões são abertas sob demanda, mas é o ponto que a spec chama de "dependências configuradas corretamente" (0,75).
8. **Rede única.** Todos os serviços veem todos. Duas redes (uma para frontend e backend, outra para os dados) seriam mais seguras.
9. **Portas de dados expostas no host** (5432, 6379, 5672). Úteis para estudo, desnecessárias para o funcionamento e arriscadas numa VM com IP público.
10. **MinIO e backend sem healthcheck.** O MinIO usa `service_started` e a imagem é `cgr.dev/chainguard/minio:latest`, sem versão fixa.
11. **Conta root do MinIO usada como chave da aplicação.**

### Dockerfiles

12. **Backend e worker não têm `.dockerignore`.** O `COPY . .` leva para a imagem qualquer `.env`, `.venv` ou `db.sqlite3` que existir na pasta local. Só o frontend tem `.dockerignore`.
13. **Backend roda `runserver` (desenvolvimento) como root.** O `gunicorn` está no `requirements.txt` e não é usado. `gcc` e `libpq-dev` são desnecessários com `psycopg2-binary`.
14. **`tenacity` não está em `worker/requirements.txt`** (chega via `google-genai`). Declarar explicitamente.

### Documentação e código desatualizados (resquícios do trabalho 1)

15. `backend/README.md` cita `S3_BUCKET` e `services/s3.py` (hoje é `minIO.py`, e a variável é `MINIO_BUCKET`).
16. `backend/articles/tests/integration/README.md`, `test_especificacao.py` e `test_pipeline_e2e.py` ainda verificam S3, SNS e SQS (`S3_BUCKET`, `SNS_TOPIC_ARN`, `SQS_QUEUE_URL`). Esses testes só rodam com variáveis de integração ligadas; os de MinIO e RabbitMQ (`test_s3.py`, `test_rabbitmq.py`) já foram migrados.
17. `docs/aws/*` descreve o trabalho 1 e continua válido como histórico.
18. `.env.example`: `MINIO_PUBLIC_ENDPOINT_URL` termina com espaço; há comentários na mesma linha de valores (`DJANGO_SECRET_KEY=troque-isto   # ...`); e `DB_USER` e `POSTGRES_USER` precisam ser preenchidos com o mesmo valor (o `.env.example` deixa os dois vazios).
19. O `docker-compose.yml` e o `deploy.yml` não executam os testes.

### Extra (+1 ponto)

20. Não há manifestos Kubernetes. O extra pede Deployment e Services (NodePort e ClusterIP) e uso seguro de Secrets. Mapeamento natural: `frontend` como NodePort; `backend`, `postgres`, `minio`, `rabbitmq`, `redis` como ClusterIP; senhas em `Secret` e o restante em `ConfigMap`.

## Perguntas gerais para treinar

1. **Qual a vantagem de containers em relação a instalar tudo na máquina?** Ambiente reproduzível: mesma imagem em qualquer lugar, dependências isoladas, subida com um comando.
2. **Container é uma VM?** Não. Compartilha o kernel do host; é um processo isolado, mais leve.
3. **Como o backend encontra o banco?** Pelo nome do serviço (`postgres`) na rede `artigos-network`.
4. **Por que o `.env` não está na imagem nem no Git?** Tem segredos; a imagem deve ser a mesma em qualquer ambiente e a configuração entra na execução.
5. **O que acontece se eu rodar `docker compose down`?** Remove containers e rede; os volumes (banco, PDFs, filas) ficam. `down -v` apaga tudo.
6. **Como o PDF chega ao usuário?** O backend gera uma URL pré-assinada do MinIO (endereço público, 300 s) e o navegador baixa direto dele.
7. **Por que há duas URLs do MinIO (`MINIO_ENDPOINT_URL` e `MINIO_PUBLIC_ENDPOINT_URL`)?** A interna só existe dentro da rede do Docker; a pública é a que o navegador alcança. A URL assinada deve nascer com a pública.
8. **Por que o RabbitMQ e não o Kafka?** Familiaridade e, tecnicamente, o problema é fila de tarefas com um consumidor. Ver [rabbitmq.md](rabbitmq.md).
9. **O que acontece se o worker cair durante o processamento?** A mensagem não recebeu `ack`, então o RabbitMQ a devolve à fila. Como a fila é persistente (volume `rabbitmq_data`), ela sobrevive até a um restart do broker.
10. **O que acontece se o RabbitMQ estiver fora na hora do cadastro?** A publicação falha, o artigo vira `ERRO` e a API responde 503; o dono pode usar `POST /articles/<id>/reprocess/`.
11. **E se o Redis cair? E o DynamoDB?** A API continua. Sem Redis, as leituras vão ao banco; sem DynamoDB, só o log se perde.
12. **Por que o worker é um container separado?** Outro papel e outras dependências; escala independente e não segura requisições HTTP.
13. **O que mudou no código do trabalho 1 para o 2?** `boto3` com `endpoint_url` para o MinIO, `pika` no lugar do SNS/SQS, Postgres com host `postgres`, front servido por Nginx com `/api` e os Dockerfiles/compose. A regra de negócio não mudou.
14. **Como escalar a API?** Mais réplicas do `backend` atrás do Nginx ou de um balanceador. Hoje o Nginx aponta para um único nome (`backend`) e o `container_name` fixo impede `--scale`; no Kubernetes, um Deployment com réplicas e um Service resolveria.
15. **O que você mudaria para produção?** `gunicorn`, usuário não root, `.dockerignore`, versões fixas das imagens, healthchecks em todos os serviços, rede segmentada, sem portas de dados no host, HTTPS, usuário de serviço no MinIO, segredos em um cofre (ou Secrets do Kubernetes).

[← 6. CI e deploy](06-ci-deploy.md) | [Índice](README.md)
