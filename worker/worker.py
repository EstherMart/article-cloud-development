"""Worker que consome eventos do RabbitMQ, processa artigos e grava o resultado no Postgres.

A fila e a DLQ são declaradas aqui e no backend (`backend/articles/services/messaging.py`) com argumentos
IDÊNTICOS: se um lado mudar sem o outro, o RabbitMQ recusa a segunda declaração (PRECONDITION_FAILED).
Detalhes e motivos em docs/docker/rabbitmq.md.
"""
import json
import logging
import os
import time
from io import BytesIO

import boto3
import pika
import psycopg2
import redis
from google import genai
from pypdf import PdfReader
from botocore.config import Config
from pika.exceptions import AMQPError

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
)

from google.genai import errors

logger = logging.getLogger(__name__)

DEFAULT_QUEUE = 'artigos.criados'
MAX_DELIVERIES = 3  # reentregas permitidas; depois da 3ª reentrega (4ª entrega) falhar, vai para a DLQ
RECONNECT_DELAY = 5

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
    """Decodifica o corpo (JSON) da mensagem e valida os campos obrigatórios."""
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError('A mensagem da fila deve conter um objeto JSON.')

    article_id = payload.get('article_id')
    if isinstance(article_id, bool) or not isinstance(article_id, int) or article_id < 1:
        raise ValueError('article_id deve ser um inteiro positivo.')
    for field in ('s3_key', 'bucket'):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f'{field} é obrigatório na mensagem.')
    return payload


def queue_name():
    return os.environ.get('RABBITMQ_QUEUE') or DEFAULT_QUEUE


def _connection_parameters():
    return pika.ConnectionParameters(
        host=os.environ.get('RABBITMQ_HOST', 'localhost'),
        port=int(os.environ.get('RABBITMQ_PORT', '5672')),
        virtual_host=os.environ.get('RABBITMQ_VHOST', '/'),
        credentials=pika.PlainCredentials(
            _required_env('RABBITMQ_DEFAULT_USER'),
            _required_env('RABBITMQ_DEFAULT_PASS'),
        ),
        # O processamento (PDF + Gemini) roda dentro do callback e bloqueia a thread que responde aos
        # heartbeats. Com o padrão (60 s), um artigo lento faria o broker derrubar a conexão no meio do
        # trabalho. Por isso o intervalo é alto.
        heartbeat=600,
        blocked_connection_timeout=300,
    )


def declare_topology(channel):
    """Fila principal (quorum, 3 entregas) + exchange e fila de mensagens mortas (DLQ). Idempotente."""
    queue = queue_name()
    dlx = f'{queue}.dlx'
    dlq = f'{queue}.dlq'

    channel.exchange_declare(exchange=dlx, exchange_type='direct', durable=True)
    channel.queue_declare(queue=dlq, durable=True)
    channel.queue_bind(queue=dlq, exchange=dlx, routing_key=queue)
    channel.queue_declare(
        queue=queue,
        durable=True,
        arguments={
            'x-queue-type': 'quorum',
            'x-delivery-limit': MAX_DELIVERIES,
            'x-dead-letter-exchange': dlx,
            'x-dead-letter-routing-key': queue,
        },
    )


def extract_text(pdf_bytes):
    """Extrai texto de um PDF; PDF escaneado sem camada de texto retorna string vazia."""
    reader = PdfReader(BytesIO(pdf_bytes))
    return '\n'.join(page.extract_text() or '' for page in reader.pages).strip()



def _is_retryable_gemini_error(exc):
    if not isinstance(exc, errors.APIError):
        return False

    status = getattr(exc, 'code', None)

    if status is None:
        status = getattr(exc, 'status_code', None)

    return status == 429 or (
        isinstance(status, int) and status >= 500
    )


@retry(
    retry=retry_if_exception(_is_retryable_gemini_error),
    wait=wait_exponential(
        multiplier=2,
        min=2,
        max=30
    ),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def translate(text, target='en'):

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
    """Processa uma mensagem ({'Body': <JSON>}); levanta exceção em falha para o chamador não confirmá-la."""
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


def handle_delivery(channel, method, body):
    """Trata uma entrega do RabbitMQ e responde ao broker:

    - sucesso: `ack` (a mensagem sai da fila);
    - mensagem inválida (JSON ruim, campo faltando): `nack` sem reenfileirar, vai direto para a DLQ,
      porque tentar de novo não adianta;
    - falha ao processar (Gemini, banco, MinIO...): `nack` com reenfileirar; depois de MAX_DELIVERIES
      reentregas o próprio RabbitMQ manda a mensagem para a DLQ.
    """
    tag = method.delivery_tag
    try:
        payload = _decode_body(body)
    except ValueError:
        logger.exception('Mensagem inválida; enviada para a DLQ sem novas tentativas.')
        channel.basic_nack(delivery_tag=tag, requeue=False)
        return

    try:
        process({'Body': body})
    except Exception:
        logger.exception('Falha ao processar o artigo %s; a mensagem volta para a fila.', payload['article_id'])
        channel.basic_nack(delivery_tag=tag, requeue=True)
        return

    channel.basic_ack(delivery_tag=tag)
    logger.info('Artigo %s processado e mensagem confirmada.', payload['article_id'])


def consume():
    """Conecta, declara a fila e consome até a conexão cair (levanta AMQPError / OSError)."""
    connection = pika.BlockingConnection(_connection_parameters())
    try:
        channel = connection.channel()
        declare_topology(channel)
        channel.basic_qos(prefetch_count=1)  # uma mensagem por vez: só recebe a próxima depois do ack
        channel.basic_consume(
            queue=queue_name(),
            on_message_callback=lambda ch, method, properties, body: handle_delivery(ch, method, body),
        )
        logger.info('Worker iniciado; aguardando mensagens na fila %s.', queue_name())
        channel.start_consuming()
    finally:
        if connection.is_open:
            connection.close()


def main():
    """Consome mensagens continuamente e só as confirma (ack) depois do processamento."""
    logging.basicConfig(
        level=os.environ.get('LOG_LEVEL', 'INFO').upper(),
        format='%(asctime)s %(levelname)s %(message)s',
    )
    while True:
        try:
            consume()
        except (AMQPError, OSError):
            logger.exception('Conexão com o RabbitMQ indisponível; nova tentativa em %s s.', RECONNECT_DELAY)
            time.sleep(RECONNECT_DELAY)


if __name__ == '__main__':
    main()
