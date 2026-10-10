# Worker

Processamento assíncrono, fora da API e fora do Auto Scaling Group. Roda em uma EC2 própria. **Só o esqueleto existe.**

## O que faz

1. Lê mensagens da fila SQS com long polling (`WaitTimeSeconds=20`).
2. Baixa o PDF do S3 e extrai o texto (`pypdf` ou `pdfplumber`).
3. Traduz o resumo (Amazon Translate). Se o PDF for escaneado e não tiver texto, usa o resumo digitado no cadastro.
4. Grava `translated_abstract` no RDS, muda o status para PROCESSADO e invalida `artigo:{id}` no Redis.
5. Só então apaga a mensagem da fila.

## Regras de robustez

- Em caso de falha: marcar o artigo como ERRO e deixar a mensagem voltar à fila.
- DLQ com 3 tentativas para mensagens que sempre falham.
- Visibility Timeout maior que o tempo de processar um PDF.
- Na assinatura SNS → SQS, ativar "raw message delivery", ou ler a mensagem real no campo `Message` do envelope do SNS.
- Mensagem sugerida: `{"article_id": 1, "s3_key": "...", "bucket": "..."}`. Fechar o formato com o back antes de implementar.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `worker.py` | Esqueleto com as funções (`receive_messages`, `extract_text`, `translate`, `save_result`, `process`, `main`). Cada docstring diz como implementar |
| `requirements.txt` | boto3, psycopg2-binary, redis e pypdf |

## Decisão: independente do Django

O worker não importa o Django. Ele tem o próprio `requirements.txt` e grava no RDS com um `UPDATE` direto, usando as mesmas variáveis `DB_*` do back. Assim a EC2 do worker não precisa do projeto inteiro, e o serviço fica desacoplado como a spec pede. O custo é que o nome da tabela e das colunas (`articles_article`, `translated_abstract`, `processing_status`) fica duplicado: se o model mudar, atualize `save_result`.

## Rodar

```
cd worker
pip install -r requirements.txt
set -a; source ../backend/.env; set +a
python worker.py
```
