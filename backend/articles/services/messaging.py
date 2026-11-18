"""Publicação no RabbitMQ do evento que o worker consome.

Mensagem: {"article_id": 1, "s3_key": "artigos/1.pdf", "bucket": "<MINIO_BUCKET>", "event": "ARTICLE_CREATED"}

A fila e a DLQ são declaradas aqui e no worker (`worker/worker.py`) com argumentos IDÊNTICOS: se um lado
mudar sem o outro, o RabbitMQ recusa a segunda declaração (PRECONDITION_FAILED). Ao mexer, edite os dois.
Detalhes e motivos em docs/docker/rabbitmq.md.
"""
import json
import os

import pika
from pika.exceptions import AMQPError

DEFAULT_QUEUE = 'artigos.criados'
MAX_DELIVERIES = 3  # reentregas permitidas; depois da 3ª reentrega (4ª entrega) falhar, vai para a DLQ


class MessagingError(RuntimeError):
    """O evento não pôde ser publicado no RabbitMQ (broker fora do ar, recusa ou mensagem sem rota)."""


def queue_name():
    return os.environ.get('RABBITMQ_QUEUE') or DEFAULT_QUEUE


def _required_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f'A variável de ambiente {name} não está configurada.')
    return value


def _connection_parameters():
    return pika.ConnectionParameters(
        host=os.environ.get('RABBITMQ_HOST', 'localhost'),
        port=int(os.environ.get('RABBITMQ_PORT', '5672')),
        virtual_host=os.environ.get('RABBITMQ_VHOST', '/'),
        credentials=pika.PlainCredentials(
            _required_env('RABBITMQ_DEFAULT_USER'),
            _required_env('RABBITMQ_DEFAULT_PASS'),
        ),
        # A requisição HTTP espera a publicação: um broker fora do ar não pode travar a API.
        socket_timeout=5,
        connection_attempts=2,
        retry_delay=1,
        blocked_connection_timeout=5,
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


def publish_article_created(article_id, s3_key, bucket):
    """Publica o evento que pede ao worker para processar um artigo.

    Levanta MessagingError (ou RuntimeError, se faltar configuração) quando não consegue entregar.
    """
    message = {
        'article_id': article_id,
        's3_key': s3_key,
        'bucket': bucket,
        'event': 'ARTICLE_CREATED',
    }
    parameters = _connection_parameters()

    try:
        # Uma conexão por publicação: BlockingConnection não é thread-safe e o volume é baixo.
        connection = pika.BlockingConnection(parameters)
        try:
            channel = connection.channel()
            channel.confirm_delivery()  # só volta depois que o broker confirma que guardou a mensagem
            declare_topology(channel)
            channel.basic_publish(
                exchange='',
                routing_key=queue_name(),
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    content_type='application/json',
                    delivery_mode=pika.DeliveryMode.Persistent,
                ),
                mandatory=True,  # sem fila para receber, levanta erro em vez de descartar em silêncio
            )
        finally:
            if connection.is_open:
                connection.close()
    except (AMQPError, OSError) as exc:
        raise MessagingError(f'Falha ao publicar no RabbitMQ: {exc!r}') from exc
