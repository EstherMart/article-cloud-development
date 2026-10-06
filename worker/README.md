# Worker

Processamento assíncrono, fora da API e fora do Auto Scaling Group. Roda em uma EC2 própria. **Ainda não implementado.**

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
