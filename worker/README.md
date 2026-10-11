# Worker

Processamento assíncrono, fora da API e fora do Auto Scaling Group. Roda em uma EC2 própria.

## O que faz

1. Lê mensagens da fila SQS com long polling (`WaitTimeSeconds=20`).
2. Marca o artigo como `PROCESSANDO`, baixa o PDF do S3 e extrai o texto com `pypdf`.
3. Traduz com Gemini o resumo digitado no cadastro; se estiver vazio, usa o texto extraído do PDF.
4. Grava `translated_abstract` no RDS, muda o status para PROCESSADO e invalida `artigo:{id}` no Redis.
5. Só então apaga a mensagem da fila.

## Regras de robustez

- Em caso de falha: marcar o artigo como `ERRO`, registrar a exceção no log e deixar a mensagem voltar à fila.
- DLQ com 3 tentativas para mensagens que sempre falham.
- Visibility Timeout maior que o tempo de processar um PDF.
- O worker aceita entrega bruta do SNS ou o envelope SNS com o corpo no campo `Message`.
- Formato esperado: `{"article_id": 1, "s3_key": "artigos/1.pdf", "bucket": "nome-do-bucket"}`.
- A mesma mensagem pode ser entregue novamente. Gravar a tradução e o status é idempotente; a mensagem só é apagada depois do processamento.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `worker.py` | Consumo SQS, extração do PDF, tradução, atualização do RDS e invalidação do Redis |
| `requirements.txt` | boto3, psycopg2-binary, redis, pypdf e google-genai |

## Decisão: independente do Django

O worker não importa o Django. Ele tem o próprio `requirements.txt` e grava no RDS com um `UPDATE` direto, usando as mesmas variáveis `DB_*` do back. Assim a EC2 do worker não precisa do projeto inteiro, e o serviço fica desacoplado como a spec pede. O custo é que o nome da tabela e das colunas (`articles_article`, `abstract`, `translated_abstract`, `processing_status`) fica duplicado: se o model mudar, atualize as consultas SQL do worker.

## Variáveis necessárias

Configure no ambiente do processo:

- `AWS_REGION`: região AWS, por exemplo `us-east-1`.
- `SQS_QUEUE_URL`: URL da fila principal.
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` e `DB_PORT`: conexão com o PostgreSQL do RDS. `DB_SSLMODE` é opcional e assume `require`.
- `REDIS_URL`: endpoint Redis, por exemplo `redis://<endpoint>:6379/0`.
- `GEMINI_API_KEY` e `GEMINI_MODEL`: credencial e nome do modelo Gemini usados pela função `translate`.

Na EC2, o boto3 usa as credenciais concedidas pelo instance profile/IAM Role para acessar SQS e S3; não coloque chaves AWS no código.

## Rodar

```
cd worker
pip install -r requirements.txt
# No Linux, carregue as variáveis de ambiente antes de iniciar:
# Inclua GEMINI_API_KEY e GEMINI_MODEL no ambiente; elas não estão no .env.example do backend.
set -a; source ../backend/.env; set +a
python worker.py
```
