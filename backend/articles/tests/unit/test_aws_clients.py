import os
from unittest import mock

from django.test import SimpleTestCase

from articles.services import aws


class AwsClientFactoryTests(SimpleTestCase):
    """Fábrica boto3: cache, região e configuração. Não usa a rede nem credenciais reais."""

    def setUp(self):
        aws._client.cache_clear()
        patcher = mock.patch.dict(os.environ, {
            'AWS_ACCESS_KEY_ID': 'teste',
            'AWS_SECRET_ACCESS_KEY': 'teste',
            'AWS_REGION': 'us-east-1',
        })
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(aws._client.cache_clear)

    def test_reaproveita_o_cliente_do_mesmo_servico(self):
        self.assertIs(aws.client('sqs'), aws.client('sqs'))

    def test_servicos_diferentes_geram_clientes_diferentes(self):
        self.assertIsNot(aws.client('sqs'), aws.client('sns'))

    def test_usa_a_regiao_do_ambiente(self):
        with mock.patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}):
            self.assertEqual(aws.client('sqs').meta.region_name, 'us-west-2')

    def test_regiao_padrao_e_us_east_1(self):
        with mock.patch.dict(os.environ):
            os.environ.pop('AWS_REGION')
            self.assertEqual(aws.client('sqs').meta.region_name, 'us-east-1')

    def test_define_timeouts_e_retries(self):
        config = aws.client('sqs').meta.config
        self.assertEqual(config.connect_timeout, 3)
        self.assertEqual(config.read_timeout, 10)
        self.assertEqual(config.retries['mode'], 'standard')
        self.assertEqual(config.retries['total_max_attempts'], 4)  # 1 tentativa + 3 retries

    def test_s3_assina_com_signature_v4(self):
        self.assertEqual(aws.client('s3').meta.config.signature_version, 's3v4')

    def test_resource_e_reaproveitado_dentro_da_mesma_thread(self):
        self.assertIs(aws.resource('dynamodb'), aws.resource('dynamodb'))
