import json

from django.contrib.auth.models import User
from django.test import TestCase


class ApiTestCase(TestCase):
    """Base dos testes de API: um usuário e helpers para enviar JSON."""

    USERNAME = 'teste'

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username=cls.USERNAME, password='123456')

    def post_article(self, **overrides):
        body = {
            'title': 'Introdução à Nuvem',
            'authors': ['Ana', 'Bruno'],
            'area': 'Computação',
            'user': self.USERNAME,
            'tags': ['AWS', 'Python'],
        }
        body.update(overrides)
        return self.send('post', '/articles/', body)

    def create_article(self, **overrides):
        """Cria um artigo pela API e devolve o id."""
        return self.post_article(**overrides).json()['article']['id']

    def send(self, method, url, body):
        return getattr(self.client, method)(
            url, data=json.dumps(body), content_type='application/json'
        )
