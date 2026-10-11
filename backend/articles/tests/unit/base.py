import json
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.tokens import make_token

PDF_BYTES = b'%PDF-1.4 teste'


class ApiTestCase(TestCase):
    """Base dos testes de API: usuário autenticado, AWS simulada e helpers de requisição."""

    USERNAME = 'teste'

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username=cls.USERNAME, password='senha-forte-123')

    def setUp(self):
        self.s3 = mock.Mock()
        self.sns = mock.Mock()
        self.s3.generate_presigned_url.return_value = 'https://s3.exemplo/arquivo.pdf'
        self.start_patch('articles.services.s3.client', return_value=self.s3)
        self.start_patch('articles.services.messaging.client', return_value=self.sns)
        self.start_patch('articles.views.log_action')
        self.start_patch('articles.views.invalidate_article')
        self.start_patch('articles.views.get_or_set', side_effect=lambda key, loader, ttl=None: loader())
        env_patcher = mock.patch.dict('os.environ', {'SNS_TOPIC_ARN': 'arn:aws:sns:us-east-1:123456789012:artigos'})
        env_patcher.start()
        self.addCleanup(env_patcher.stop)
        self.login_as(self.user)

    def start_patch(self, target, **kwargs):
        patcher = mock.patch(target, **kwargs)
        started = patcher.start()
        self.addCleanup(patcher.stop)
        return started

    def login_as(self, user):
        self.client.defaults['HTTP_AUTHORIZATION'] = 'Token ' + make_token(user)

    def logout(self):
        self.client.defaults.pop('HTTP_AUTHORIZATION', None)

    def post_article(self, **overrides):
        """POST multipart com PDF. Passe `file=None` para enviar sem arquivo."""
        fields = {
            'title': 'Introdução à Nuvem',
            'authors': ['Ana', 'Bruno'],
            'area': 'Computação',
            'tags': ['AWS', 'Python'],
            'abstract': '',
            'file': SimpleUploadedFile('artigo.pdf', PDF_BYTES, content_type='application/pdf'),
        }
        fields.update(overrides)
        data = {name: value for name, value in fields.items() if value is not None}
        for name in ('authors', 'tags'):
            if name in data and not isinstance(data[name], str):
                data[name] = json.dumps(data[name])
        return self.client.post('/articles/', data=data)

    def create_article(self, **overrides):
        """Cria um artigo pela API e devolve o id."""
        return self.post_article(**overrides).json()['article']['id']

    def send(self, method, url, body):
        return getattr(self.client, method)(
            url, data=json.dumps(body), content_type='application/json'
        )
