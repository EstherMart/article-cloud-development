# Worker

Processa os artigos fora da API. Não importa o Django: tem o próprio `requirements.txt` e atualiza o banco com SQL direto. Roda em container (`worker/Dockerfile`, serviço `worker` do `docker-compose.yml`).

## O que faz

1. Consome a fila do RabbitMQ, uma mensagem por vez (`prefetch_count=1`, ack manual).
2. Marca o artigo como `PROCESSANDO`, baixa o PDF do MinIO e extrai o texto com `pypdf`.
3. Traduz para o inglês com o Gemini o resumo digitado no cadastro. Se o resumo estiver vazio, traduz o texto extraído do PDF. PDF escaneado sem resumo não tem o que traduzir e termina em `ERRO`.
4. Grava `translated_abstract` no Postgres, marca o artigo como `PROCESSADO` e apaga `artigo:{id}` do Redis.
5. Só então confirma a mensagem (`ack`).

Se algo falhar, o artigo vira `ERRO` e a mensagem volta à fila (`nack`). Depois de 3 reentregas o RabbitMQ a envia à DLQ `artigos.criados.dlq`. Mensagem inválida (JSON ruim, campo faltando) vai direto à DLQ. A mesma mensagem pode chegar duas vezes, e o resultado é o mesmo. Se a conexão cair, o worker reconecta sozinho. Detalhes em [docs/docker/rabbitmq.md](../docs/docker/rabbitmq.md).

Mensagem esperada: `{"article_id": 1, "s3_key": "artigos/1.pdf", "bucket": "nome-do-bucket"}`.

## Variáveis de ambiente

| Variável | Uso |
|---|---|
| `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_DEFAULT_USER`, `RABBITMQ_DEFAULT_PASS`, `RABBITMQ_QUEUE` | Broker e fila (padrão `localhost`, `5672`, `artigos.criados`) |
| `MINIO_ENDPOINT_URL`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | MinIO, de onde vem o PDF |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `DB_SSLMODE` | Postgres (`DB_SSLMODE` padrão `require`; use `disable` no container do compose) |
| `REDIS_URL` | Cache a invalidar. Se falhar, só registra no log (o cache expira em 5 minutos) |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Tradução. A chave é segredo: fica só no ambiente do worker |

O worker precisa de acesso de saída à internet (HTTPS) para falar com o Gemini.

## Rodar

```
cd worker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../backend/.env; set +a      # mais GEMINI_API_KEY e GEMINI_MODEL
python worker.py
```

## Testes

```
python -m unittest discover -s tests -v                                          # sem broker e sem Gemini
RUN_GEMINI=1 python -m unittest discover -s tests -p 'test_gemini_real.py' -v    # Gemini de verdade
```

`tests/test_worker.py` cobre a extração (5 e 30 páginas, escaneado, misto, corrompido, acentos) e o resultado do `process()` em cada cenário. `tests/test_gemini_real.py` confere o que a tradução não pode estragar: termos técnicos, números e idioma. Os PDFs vêm de `backend/articles/tests/fixtures/pdfs`.
