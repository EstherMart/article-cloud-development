"""Worker que consome eventos da SQS, processa artigos e grava o resultado no RDS."""
import json
import logging
import os
import time
from io import BytesIO

import boto3
import psycopg2
import redis
from google import genai
from pypdf import PdfReader
from botocore.config import Config

logger = logging.getLogger(__name__)

# minIO client
def _minio_client():
    return boto3.client(
        's3',
        endpoint_url = _required_env('MINIO_ENDPOINT_URL'),
        aws_access_key_id = _required_env('MINIO_ROOT_USER'),
        aws_secret_access_key = _required_env('MINIO_ROOT_PASSWORD'),
        region_name = os.environ.get('MINIO_REGION', 'us-east-1'),
        config = Config(signature_version = 's3v4', s3 = {'addressing_style': 'path'})
    )

def _required_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f'A variável de ambiente {name} é obrigatória.')
    return value


def _database_connection():
    return psycopg2.connect(
        host=_required_env('DB_HOST'),
        dbname=_required_env('DB_NAME'),
        user=_required_env('DB_USER'),
        password=_required_env('DB_PASSWORD'),
        port=os.environ.get('DB_PORT', '5432'),
        sslmode=os.environ.get('DB_SSLMODE', 'require'),
    )


def _decode_body(body):
    """Decodifica uma mensagem JSON direta ou o envelope SNS."""
    payload = json.loads(body)
    if isinstance(payload, dict) and isinstance(payload.get('Message'), str):
        payload = json.loads(payload['Message'])
    if not isinstance(payload, dict):
        raise ValueError('A mensagem da fila deve conter um objeto JSON.')

    article_id = payload.get('article_id')
    if isinstance(article_id, bool) or not isinstance(article_id, int) or article_id < 1:
        raise ValueError('article_id deve ser um inteiro positivo.')
    for field in ('s3_key', 'bucket'):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f'{field} é obrigatório na mensagem.')
    return payload


def receive_messages(sqs, queue_url):
    """Faz long polling na SQS e devolve as mensagens recebidas."""
    response = sqs.receive_message(
        QueueUrl=queue_url,
        WaitTimeSeconds=20,
        MaxNumberOfMessages=1,
        AttributeNames=['ApproximateReceiveCount'],
    )
    return response.get('Messages', [])


def extract_text(pdf_bytes):
    """Extrai texto de um PDF; PDF escaneado sem camada de texto retorna string vazia."""
    reader = PdfReader(BytesIO(pdf_bytes))
    return '\n'.join(page.extract_text() or '' for page in reader.pages).strip()


def translate(text, target='en'):
    """Traduz texto com Gemini. Configure GEMINI_API_KEY e GEMINI_MODEL."""
    if not text.strip():
        return ''

    client = genai.Client(api_key=_required_env('GEMINI_API_KEY'))
    response = client.models.generate_content(
        model=_required_env('GEMINI_MODEL'),
        contents=(
            f"Traduza o texto para o idioma de código '{target}'. "
            'Retorne somente a tradução, sem explicações.\n\n'
            f'{text}'
        ),
    )

    if not response.text:
        raise RuntimeError('O Gemini não retornou uma tradução.')

    return response.text.strip()


def save_result(article_id, translated_abstract, status):
    """Grava a tradução e o status final no registro do artigo."""
    if status not in {'PROCESSADO', 'ERRO'}:
        raise ValueError(f'Status final inválido: {status}')

    with _database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE articles_article
                SET translated_abstract = %s, processing_status = %s
                WHERE id = %s
                ''',
                (translated_abstract, status, article_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f'Artigo {article_id} não encontrado no banco.')


def _set_status(article_id, status):
    if status not in {'PROCESSANDO', 'ERRO'}:
        raise ValueError(f'Status intermediário inválido: {status}')

    with _database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'UPDATE articles_article SET processing_status = %s WHERE id = %s',
                (status, article_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f'Artigo {article_id} não encontrado no banco.')


def _get_abstract(article_id):
    with _database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT abstract FROM articles_article WHERE id = %s',
                (article_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError(f'Artigo {article_id} não encontrado no banco.')
            return row[0] or ''


def _invalidate_cache(article_id):
    client = redis.Redis.from_url(
        _required_env('REDIS_URL'),
        socket_connect_timeout=3,
        socket_timeout=3,
        decode_responses=True,
    )
    client.delete(f'artigo:{article_id}', 'artigos:recentes')
    for key in client.scan_iter(match='busca:*'):
        client.delete(key)


def process(message):
    """Processa uma mensagem; levanta exceção em falha para a SQS tentar novamente."""
    payload = _decode_body(message['Body'])
    article_id = payload['article_id']

    try:
        _set_status(article_id, 'PROCESSANDO')
        abstract = _get_abstract(article_id)

        s3 = _minio_client()
        response = s3.get_object(Bucket=payload['bucket'], Key=payload['s3_key'])
        pdf_stream = response['Body']
        try:
            extracted_text = extract_text(pdf_stream.read())
        finally:
            pdf_stream.close()

        # O resumo digitado é a fonte preferida; o texto do PDF é um fallback.
        source_text = abstract.strip() or extracted_text
        if not source_text:
            raise ValueError(
                f'O artigo {article_id} não tem resumo cadastrado e o PDF não contém texto extraível.'
            )

        translated_abstract = translate(source_text)
        save_result(article_id, translated_abstract, 'PROCESSADO')

        try:
            _invalidate_cache(article_id)
        except (redis.RedisError, RuntimeError):
            logger.exception(
                'Não foi possível invalidar o cache do artigo %s; as chaves expiram pelo TTL.',
                article_id,
            )
    except Exception:
        try:
            _set_status(article_id, 'ERRO')
        except Exception:
            logger.exception('Também falhou ao marcar o artigo %s como ERRO.', article_id)
        raise


def main():
    """Consome mensagens continuamente e só as apaga depois do processamento."""
    logging.basicConfig(
        level=os.environ.get('LOG_LEVEL', 'INFO').upper(),
        format='%(asctime)s %(levelname)s %(message)s',
    )
    queue_url = _required_env('SQS_QUEUE_URL')
    region = os.environ.get('AWS_REGION', 'us-east-1')
    sqs = boto3.client('sqs', region_name=region)

    logger.info('Worker iniciado; aguardando mensagens na fila SQS.')
    while True:
        try:
            messages = receive_messages(sqs, queue_url)
        except Exception:
            logger.exception('Falha ao consultar a fila SQS.')
            time.sleep(5)
            continue

        for message in messages:
            receipt_handle = message.get('ReceiptHandle')
            if not receipt_handle:
                logger.error('Mensagem recebida sem ReceiptHandle; não é possível removê-la da fila.')
                continue

            try:
                payload = _decode_body(message['Body'])
                process(message)
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                logger.info('Artigo %s processado e mensagem removida da fila.', payload['article_id'])
            except Exception:
                logger.exception('Falha ao processar mensagem; a SQS poderá entregá-la novamente.')


if __name__ == '__main__':
    main()
