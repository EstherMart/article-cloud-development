import json
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.tokens import make_token

PDF_BYTES = b'%PDF-1.4 teste'


class ApiTestCase(TestCase):
    """Base dos testes de API: um usuário autenticado, o S3 simulado e helpers de requisição."""

    USERNAME = 'teste'

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username=cls.USERNAME, password='senha-forte-123')

    def setUp(self):
        patcher = mock.patch('articles.views.boto3')
        self.boto3 = patcher.start()
        self.addCleanup(patcher.stop)
        self.s3 = self.boto3.client.return_value
        self.s3.generate_presigned_url.return_value = 'https://s3.exemplo/arquivo.pdf'
        self.login_as(self.user)

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
