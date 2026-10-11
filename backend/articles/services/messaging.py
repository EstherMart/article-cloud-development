"""Publicação de eventos no SNS.

A API publica e responde, sem esperar o worker. O SNS entrega na fila SQS
(assinatura com raw message delivery) e o worker consome.

Formato da mensagem (fechar com o worker, que lê este mesmo formato):
    {"article_id": 1, "s3_key": "artigos/1.pdf", "bucket": "<S3_BUCKET>", "event": "ARTICLE_CREATED"}

Tópico em SNS_TOPIC_ARN.
"""
import os
import json

from .aws import client


def publish_article_created(article_id, s3_key, bucket):
    """Publica no SNS o evento que pede ao worker para processar um artigo."""
    topic_arn = os.environ.get('SNS_TOPIC_ARN')
    if not topic_arn:
        raise RuntimeError('A variável de ambiente SNS_TOPIC_ARN não está configurada.')

    message = {
        'article_id': article_id,
        's3_key': s3_key,
        'bucket': bucket,
        'event': 'ARTICLE_CREATED',
    }
    return client('sns').publish(
        TopicArn=topic_arn,
        Message=json.dumps(message),
    )
