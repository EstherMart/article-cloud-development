"""RabbitMQ de verdade (requisito de mensageria do trabalho 2): publica, consome, reentrega e DLQ.

Desligado por padrão. Suba o broker (`docker compose up -d rabbitmq`) e rode, com o .env carregado:

    RUN_RABBITMQ_INTEGRATION=1 RABBITMQ_HOST=localhost python manage.py test articles.tests.integration.test_rabbitmq

Cada teste usa uma fila só dele (nome aleatório) e apaga tudo no fim, então pode rodar com o worker no ar.
"""
import json
import os
import unittest
import uuid
from unittest import mock

import pika

from .base import novo_article_id


@unittest.skipUnless(os.environ.get('RUN_RABBITMQ_INTEGRATION') == '1',
                     'desligado: defina RUN_RABBITMQ_INTEGRATION=1 (e suba o RabbitMQ)')
class RabbitMQTests(unittest.TestCase):

    def setUp(self):
        for name in ('RABBITMQ_DEFAULT_USER', 'RABBITMQ_DEFAULT_PASS'):
            if not os.environ.get(name):
                self.skipTest(f'defina {name} no .env')

        from articles.services import messaging

        self.messaging = messaging
        self.queue = f'teste.{uuid.uuid4().hex[:8]}'
        patcher = mock.patch.dict(os.environ, {'RABBITMQ_QUEUE': self.queue})
        patcher.start()
        self.addCleanup(patcher.stop)

        self.connection = pika.BlockingConnection(messaging._connection_parameters())
        self.addCleanup(self._close)
        self.channel = self.connection.channel()
        self.addCleanup(self._cleanup_broker)
        self.article_id = novo_article_id()

    def _cleanup_broker(self):
        for queue in (self.queue, f'{self.queue}.dlq'):
            self.channel.queue_delete(queue=queue)
        self.channel.exchange_delete(exchange=f'{self.queue}.dlx')

    def _close(self):
        if self.connection.is_open:
            self.connection.close()

    def _publicar(self):
        self.messaging.publish_article_created(self.article_id, f'artigos/{self.article_id}.pdf', 'artigos')

    def test_publicacao_chega_na_fila_com_o_json_do_evento(self):
        self._publicar()

        method, properties, body = self.channel.basic_get(queue=self.queue, auto_ack=False)
        self.assertIsNotNone(method, 'a mensagem não chegou na fila')
        self.channel.basic_ack(method.delivery_tag)
        self.assertEqual(json.loads(body), {
            'article_id': self.article_id, 's3_key': f'artigos/{self.article_id}.pdf',
            'bucket': 'artigos', 'event': 'ARTICLE_CREATED',
        })
        self.assertEqual(properties.delivery_mode, 2, 'a mensagem deve ser persistente')

    def test_declarar_a_topologia_de_novo_e_idempotente(self):
        # Backend e worker declaram a mesma fila. Se os argumentos divergissem, o broker responderia
        # PRECONDITION_FAILED. Aqui o publicador declara duas vezes seguidas sem erro.
        self._publicar()
        self._publicar()

        self.assertEqual(self.channel.queue_declare(queue=self.queue, passive=True).method.message_count, 2)

    def test_mensagem_nao_confirmada_volta_e_vai_para_a_dlq_depois_do_limite_de_entregas(self):
        self._publicar()

        entregas = 0
        while True:
            method, _, _ = self.channel.basic_get(queue=self.queue, auto_ack=False)
            if method is None:
                break
            entregas += 1
            self.assertLessEqual(entregas, 10, 'a mensagem nunca saiu da fila principal')
            self.channel.basic_nack(method.delivery_tag, requeue=True)

        self.assertEqual(entregas, self.messaging.MAX_DELIVERIES + 1)  # a original + 3 reentregas
        method, _, body = self.channel.basic_get(queue=f'{self.queue}.dlq', auto_ack=True)
        self.assertIsNotNone(method, 'a mensagem não chegou na DLQ')
        self.assertEqual(json.loads(body)['article_id'], self.article_id)

    def test_nack_sem_reenfileirar_manda_direto_para_a_dlq(self):
        self._publicar()

        method, _, _ = self.channel.basic_get(queue=self.queue, auto_ack=False)
        self.channel.basic_nack(method.delivery_tag, requeue=False)

        self.assertIsNone(self.channel.basic_get(queue=self.queue, auto_ack=True)[0])
        method, _, body = self.channel.basic_get(queue=f'{self.queue}.dlq', auto_ack=True)
        self.assertIsNotNone(method, 'a mensagem não chegou na DLQ')
        self.assertEqual(json.loads(body)['article_id'], self.article_id)

    def test_publicar_com_o_broker_fora_do_ar_levanta_messaging_error(self):
        with mock.patch.dict(os.environ, {'RABBITMQ_HOST': 'host-que-nao-existe.invalid'}):
            with self.assertRaises(self.messaging.MessagingError):
                self._publicar()
