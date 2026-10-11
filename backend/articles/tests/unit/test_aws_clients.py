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


    def test_s3_assina_com_signature_v4(self):
        self.assertEqual(aws.client('s3').meta.config.signature_version, 's3v4')
