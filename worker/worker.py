"""Worker: consome a fila SQS, extrai o texto do PDF e traduz o resumo.

Roda em uma EC2 própria, fora do Auto Scaling Group, e não depende do Django.
Lê as mesmas variáveis de ambiente do back (ver backend/.env.example).
Branch: feat/sns-sqs-worker.

Fluxo de cada mensagem (ver README.md da raiz):
    1. receber a mensagem (long polling);
    2. marcar o artigo como PROCESSANDO;
    3. baixar o PDF do S3 e extrair o texto;
    4. traduzir o resumo;
    5. gravar translated_abstract e status PROCESSADO no RDS;
    6. invalidar artigo:{id} no Redis;
    7. só então apagar a mensagem da fila.
Em caso de erro: marcar ERRO e NÃO apagar a mensagem. Ela volta à fila depois do
Visibility Timeout e, após 3 tentativas, vai para a DLQ.
"""
import json
import os
from google import genai


def receive_messages(sqs, queue_url):
    """Long polling: sqs.receive_message(QueueUrl=..., WaitTimeSeconds=20, MaxNumberOfMessages=1).

    Com raw message delivery ligado, json.loads(msg['Body']) já é o corpo
    {"article_id": ..., "s3_key": ..., "bucket": ...}. Sem raw delivery, o corpo é
    o envelope do SNS e a mensagem real está em json.loads(body)['Message'].
    """
    raise NotImplementedError


def extract_text(pdf_bytes):
    """Extrai o texto com pypdf.PdfReader. PDF escaneado não tem texto: devolva ''
    e o chamador usa o resumo digitado no cadastro."""
    raise NotImplementedError


def translate(text, target='en'):
    """Traduz com Amazon Translate: boto3.client('translate').translate_text(
    Text=..., SourceLanguageCode='pt', TargetLanguageCode=target).
    Alternativa gratuita: deep-translator. O Translate limita o tamanho do texto,
    então traduza só o resumo."""
    if not text.strip():
        return ''

    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    model = os.environ['GEMINI_MODEL']

    response = client.models.generate_content(
        model=model,
        contents=(
            f"Traduza o texto para o idioma de código '{target}'. "
            "Retorne somente a tradução, sem explicações.\n\n"
            f"{text}"
        ),
    )

    if not response.text:
        raise RuntimeError('O Gemini não retornou uma tradução.')

    return response.text.strip()


def save_result(article_id, translated_abstract, status):
    """UPDATE direto no RDS com psycopg2, usando as variáveis DB_*:
    UPDATE articles_article SET translated_abstract=%s, processing_status=%s WHERE id=%s.
    O nome da tabela vem do Django: app `articles`, model `Article`."""
    raise NotImplementedError


def process(message):
    """Executa os passos 2 a 6 de uma mensagem. Se levantar exceção, o loop principal
    marca ERRO e não apaga a mensagem."""
    raise NotImplementedError


def main():
    """Loop infinito: receive_messages -> process -> delete_message.
    Apague a mensagem (sqs.delete_message com o ReceiptHandle) só depois do passo 5."""
    raise NotImplementedError


if __name__ == '__main__':
    main()
