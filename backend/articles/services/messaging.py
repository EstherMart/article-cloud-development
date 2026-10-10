"""Publicação de eventos no SNS.

A API publica e responde, sem esperar o worker. O SNS entrega na fila SQS
(assinatura com raw message delivery) e o worker consome.

Formato da mensagem (fechar com o worker, que lê este mesmo formato):
    {"article_id": 1, "s3_key": "artigos/1.pdf", "bucket": "<S3_BUCKET>", "event": "ARTICLE_CREATED"}

Tópico em SNS_TOPIC_ARN.
"""
import json

from .aws import client


def publish_article_created(article_id, s3_key, bucket):
    """Publica ARTICLE_CREATED.

    Como fazer: client('sns').publish(TopicArn=..., Message=json.dumps(corpo)).
    Se a publicação falhar, o artigo fica PENDENTE sem processar: marque ERRO
    ou decida em grupo se tenta de novo.
    """
    raise NotImplementedError
