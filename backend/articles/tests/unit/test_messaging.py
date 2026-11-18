"""Publicador do RabbitMQ (articles/services/messaging.py), sem broker de verdade."""
import json
import os
from unittest import mock

import pika
import pika.exceptions
from django.test import SimpleTestCase

from articles.services import messaging

ENV = {
    'RABBITMQ_HOST': 'rabbitmq', 'RABBITMQ_DEFAULT_USER': 'teste', 'RABBITMQ_DEFAULT_PASS': 'senha',
    'RABBITMQ_QUEUE': 'fila.teste',
}


class PublicadorTests(SimpleTestCase):

    def setUp(self):
        patcher = mock.patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.connection = mock.Mock()
        self.channel = self.connection.channel.return_value
        patcher = mock.patch('articles.services.messaging.pika.BlockingConnection', return_value=self.connection)
        self.blocking = patcher.start()
        self.addCleanup(patcher.stop)

    def publicar(self):
        messaging.publish_article_created(7, 'artigos/7.pdf', 'bucket-teste')

    def test_publica_json_persistente_na_fila_e_com_confirmacao(self):
        self.publicar()

        self.channel.confirm_delivery.assert_called_once_with()
        kwargs = self.channel.basic_publish.call_args.kwargs
        self.assertEqual(kwargs['exchange'], '')
        self.assertEqual(kwargs['routing_key'], 'fila.teste')
        self.assertTrue(kwargs['mandatory'])
        self.assertEqual(kwargs['properties'].delivery_mode, pika.DeliveryMode.Persistent)
        self.assertEqual(json.loads(kwargs['body']), {
            'article_id': 7, 's3_key': 'artigos/7.pdf', 'bucket': 'bucket-teste', 'event': 'ARTICLE_CREATED',
        })

    def test_declara_fila_quorum_com_limite_de_entregas_e_dlq(self):
        self.publicar()

        self.channel.exchange_declare.assert_called_once_with(
            exchange='fila.teste.dlx', exchange_type='direct', durable=True)
        self.channel.queue_declare.assert_any_call(queue='fila.teste.dlq', durable=True)
        self.channel.queue_bind.assert_called_once_with(
            queue='fila.teste.dlq', exchange='fila.teste.dlx', routing_key='fila.teste')
        self.channel.queue_declare.assert_any_call(
            queue='fila.teste',
            durable=True,
            arguments={
                'x-queue-type': 'quorum',
                'x-delivery-limit': 3,
                'x-dead-letter-exchange': 'fila.teste.dlx',
                'x-dead-letter-routing-key': 'fila.teste',
            },
        )

    def test_usa_a_fila_padrao_sem_RABBITMQ_QUEUE(self):
        with mock.patch.dict(os.environ, {'RABBITMQ_QUEUE': ''}):
            self.publicar()
        self.assertEqual(self.channel.basic_publish.call_args.kwargs['routing_key'], 'artigos.criados')

    def test_fecha_a_conexao_depois_de_publicar(self):
        self.connection.is_open = True
        self.publicar()
        self.connection.close.assert_called_once_with()

    def test_fecha_a_conexao_mesmo_quando_a_publicacao_falha(self):
        self.connection.is_open = True
        self.channel.basic_publish.side_effect = pika.exceptions.UnroutableError([])
        with self.assertRaises(messaging.MessagingError):
            self.publicar()
        self.connection.close.assert_called_once_with()

    def test_erros_do_pika_viram_messaging_error(self):
        for erro in (pika.exceptions.AMQPConnectionError('fora do ar'),
                     pika.exceptions.NackError([]),
                     pika.exceptions.UnroutableError([])):
            with self.subTest(erro=type(erro).__name__):
                self.channel.basic_publish.side_effect = erro
                with self.assertRaises(messaging.MessagingError):
                    self.publicar()

    def test_falha_de_rede_do_sistema_operacional_tambem_vira_messaging_error(self):
        self.blocking.side_effect = OSError('Name or service not known')
        with self.assertRaises(messaging.MessagingError):
            self.publicar()

    def test_sem_credenciais_levanta_runtime_error_antes_de_conectar(self):
        with mock.patch.dict(os.environ, {'RABBITMQ_DEFAULT_PASS': ''}):
            with self.assertRaises(RuntimeError):
                self.publicar()
        self.blocking.assert_not_called()

    def test_messaging_error_e_um_runtime_error(self):
        # start_processing (views.py) captura RuntimeError e responde 503.
        self.assertTrue(issubclass(messaging.MessagingError, RuntimeError))
