"""SNS e SQS (requisito 6).

ATENÇÃO: estes testes leem a fila real. Mensagens de outros artigos recebidas por engano
ficam invisíveis até o visibility timeout acabar. Rode com o worker PARADO, de preferência
numa fila de teste (aponte SQS_QUEUE_URL para ela).
"""
import json
import os
import time

from .base import AwsIntegrationTestCase, slow, novo_article_id


class SnsSqsTests(AwsIntegrationTestCase):
    REQUIRED_ENV = ('SNS_TOPIC_ARN', 'SQS_QUEUE_URL')

    def setUp(self):
        from articles.services import messaging
        from articles.services.aws import client

        self.messaging = messaging
        self.sqs = client('sqs')
        self.queue = os.environ['SQS_QUEUE_URL']
        self.article_id = novo_article_id()

    def _publicar(self):
        self.messaging.publish_article_created(
            self.article_id, f'artigos/{self.article_id}.pdf', os.environ.get('S3_BUCKET', 'bucket-de-teste')
        )

    def _receber(self, queue=None, espera=25, **opcoes):
        """Espera a mensagem DESTE teste. Devolve a mensagem ou None."""
        fim = time.time() + espera
        while time.time() < fim:
            resposta = self.sqs.receive_message(
                QueueUrl=queue or self.queue, MaxNumberOfMessages=10, WaitTimeSeconds=5,
                AttributeNames=['ApproximateReceiveCount'], **opcoes,
            )
            for mensagem in resposta.get('Messages', []):
                if self._e_deste_teste(mensagem):
                    return mensagem
        return None

    def _e_deste_teste(self, mensagem):
        try:
            return json.loads(mensagem['Body']).get('article_id') == self.article_id
        except ValueError:
            return False

    def _apagar(self, mensagem, queue=None):
        self.sqs.delete_message(QueueUrl=queue or self.queue, ReceiptHandle=mensagem['ReceiptHandle'])

    def test_publicacao_chega_na_fila_com_raw_delivery(self):
        self._publicar()
        mensagem = self._receber()
        self.assertIsNotNone(mensagem, 'a mensagem não chegou: confira a assinatura e a política da fila')
        self.addCleanup(self._apagar, mensagem)
        corpo = json.loads(mensagem['Body'])
        # Com raw delivery, o corpo é o JSON original e não o envelope do SNS.
        self.assertNotIn('TopicArn', corpo)
        self.assertEqual(corpo['article_id'], self.article_id)
        self.assertEqual(corpo['s3_key'], f'artigos/{self.article_id}.pdf')
        self.assertEqual(corpo['bucket'], os.environ.get('S3_BUCKET', 'bucket-de-teste'))
        self.assertEqual(corpo['event'], 'ARTICLE_CREATED')

    def test_mensagem_nao_apagada_volta_na_fila(self):
        self._publicar()
        primeira = self._receber(VisibilityTimeout=3)
        self.assertIsNotNone(primeira)
        time.sleep(4)
        segunda = self._receber()
        self.assertIsNotNone(segunda, 'a mensagem não voltou após o visibility timeout')
        self.addCleanup(self._apagar, segunda)
        self.assertGreaterEqual(int(segunda['Attributes']['ApproximateReceiveCount']), 2)

    @slow
    def test_mensagem_que_falha_3_vezes_vai_para_a_dlq(self):
        dlq = os.environ.get('SQS_DLQ_URL')
        if not dlq:
            self.skipTest('defina SQS_DLQ_URL no .env')
        self._publicar()
        for _ in range(5):  # a mudança para a DLQ acontece ao tentar receber de novo
            self._receber(espera=6, VisibilityTimeout=1)
            time.sleep(2)
        mensagem = self._receber(queue=dlq, espera=30)
        self.assertIsNotNone(mensagem, 'a mensagem não chegou na DLQ: confira Maximum receives = 3')
        self.addCleanup(self._apagar, mensagem, dlq)
