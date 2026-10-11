import json

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.tokens import make_token, user_from_request

SENHA = 'senha-forte-123'


class AuthTestCase(TestCase):

    def post(self, path, body):
        return self.client.post(path, data=json.dumps(body), content_type='application/json')

    def register(self, **overrides):
        body = {'username': 'ana', 'email': 'ana@exemplo.com', 'password': SENHA}
        body.update(overrides)
        return self.post('/auth/register/', body)


class RegisterTests(AuthTestCase):

    def test_cria_o_usuario(self):
        self.assertEqual(self.register().status_code, 201)
        self.assertTrue(User.objects.get(username='ana').check_password(SENHA))


    def test_usuario_repetido_retorna_409_sem_diferenciar_maiusculas(self):
        self.register()
        self.assertEqual(self.register(username='ANA').status_code, 409)


class LoginTests(AuthTestCase):

    def setUp(self):
        self.register()

    def test_devolve_token_que_identifica_o_usuario(self):
        resp = self.post('/auth/login/', {'username': 'ana', 'password': SENHA})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['username'], 'ana')
        request = type('Req', (), {'headers': {'Authorization': 'Token ' + resp.json()['token']}})()
        self.assertEqual(user_from_request(request).username, 'ana')

    def test_senha_errada_retorna_401(self):
        self.assertEqual(self.post('/auth/login/', {'username': 'ana', 'password': 'errada'}).status_code, 401)


class TokenTests(TestCase):

    def request_with(self, header):
        return type('Req', (), {'headers': {'Authorization': header}})()

    def test_token_adulterado_e_recusado(self):
        user = User.objects.create_user(username='ana', password=SENHA)
        self.assertIsNone(user_from_request(self.request_with('Token ' + make_token(user) + 'x')))


class HealthCheckTests(TestCase):
    def test_health_responde_200_sem_autenticacao(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
