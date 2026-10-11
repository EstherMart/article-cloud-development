"""Fluxo completo (rode por último), de dentro da EC2 da API: API em API_BASE_URL e worker no ar.
Cria o usuário E2E_USERNAME/E2E_PASSWORD se não existir. Sem GEMINI_* no worker o artigo termina em ERRO.
"""
import json
import os
import time
import urllib.error
import urllib.request
import uuid

from .base import PDFS, AwsIntegrationTestCase


class PipelineTests(AwsIntegrationTestCase):
    REQUIRED_ENV = ('API_BASE_URL', 'S3_BUCKET', 'DYNAMODB_TABLE', 'REDIS_URL')

    def setUp(self):
        self.api = os.environ['API_BASE_URL'].rstrip('/')
        self.titulo = f'Artigo e2e {uuid.uuid4().hex[:8]}'
        self.article_id = None
        self.token = self._token()
        self.addCleanup(self._apagar)

    def _requisicao(self, metodo, caminho, corpo=None, headers=None):
        headers = dict(headers or {})
        if getattr(self, 'token', None):
            headers['Authorization'] = f'Token {self.token}'
        req = urllib.request.Request(self.api + caminho, data=corpo, method=metodo, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resposta:
            return resposta.status, json.loads(resposta.read() or b'null')

    def _json(self, metodo, caminho, dados):
        return self._requisicao(
            metodo, caminho, json.dumps(dados).encode(), {'Content-Type': 'application/json'}
        )

    def _token(self):
        credenciais = {
            'username': os.environ.get('E2E_USERNAME', 'teste-e2e'),
            'password': os.environ.get('E2E_PASSWORD', 'senha-forte-123'),
        }
        try:
            self._json('POST', '/auth/register/', credenciais)
        except urllib.error.HTTPError:
            pass  # o usuário já existe
        _, dados = self._json('POST', '/auth/login/', credenciais)
        return dados['token']

    def _cadastrar(self):
        limite = uuid.uuid4().hex
        campos = {
            'title': self.titulo,
            'authors': json.dumps(['Ana']),
            'tags': json.dumps(['AWS']),
            'area': 'Computação',
            'abstract': 'Resumo digitado para o teste de ponta a ponta.',
        }
        corpo = b''
        for nome, valor in campos.items():
            corpo += f'--{limite}\r\nContent-Disposition: form-data; name="{nome}"\r\n\r\n{valor}\r\n'.encode()
        corpo += (
            f'--{limite}\r\nContent-Disposition: form-data; name="file"; filename="artigo.pdf"\r\n'
            'Content-Type: application/pdf\r\n\r\n'
        ).encode() + (PDFS / 'artigo_nuvem.pdf').read_bytes() + f'\r\n--{limite}--\r\n'.encode()
        status, dados = self._requisicao(
            'POST', '/articles/', corpo, {'Content-Type': f'multipart/form-data; boundary={limite}'}
        )
        self.assertEqual(status, 201)
        self.article_id = dados['article']['id']
        return dados['article']

    def _apagar(self):
        if self.article_id is not None:
            try:
                self._requisicao('DELETE', f'/articles/{self.article_id}/')
            except urllib.error.HTTPError:
                pass

    def _acoes_no_dynamodb(self):
        from boto3.dynamodb.conditions import Key

        from articles.services.aws import resource

        tabela = resource('dynamodb').Table(os.environ['DYNAMODB_TABLE'])
        itens = tabela.query(KeyConditionExpression=Key('article_id').eq(str(self.article_id)))['Items']
        return [item['action'] for item in itens]

    def _esperar_processado(self, limite=90):
        fim = time.time() + limite
        while time.time() < fim:
            _, artigo = self._requisicao('GET', f'/articles/{self.article_id}/')
            if artigo['processing_status'] == 'PROCESSADO':
                return artigo
            if artigo['processing_status'] == 'ERRO':
                self.fail('o worker marcou o artigo como ERRO: veja `journalctl -u worker` (Gemini? RDS?)')
            time.sleep(3)
        self.fail('o worker não processou o artigo a tempo: confira o worker e a fila')

    def test_cadastro_ate_processado(self):
        from articles.services.aws import client

        artigo = self._cadastrar()
        self.assertEqual(artigo['processing_status'], 'PENDENTE')  # 1. RDS

        client('s3').head_object(Bucket=os.environ['S3_BUCKET'], Key=f'artigos/{self.article_id}.pdf')  # 2. S3

        self.assertEqual(self._acoes_no_dynamodb(), ['CREATE'])  # 3. DynamoDB

        processado = self._esperar_processado()  # 4. SNS, SQS, worker e RDS
        self.assertTrue(processado['translated_abstract'], 'a tradução do Gemini veio vazia')

        from articles.services import cache  # 5. Redis: a 2ª leitura vem do cache
        self._requisicao('GET', f'/articles/{self.article_id}/')
        self._requisicao('GET', f'/articles/{self.article_id}/')
        self.assertEqual(cache.get_client().exists(f'artigo:{self.article_id}'), 1)

    def test_update_loga_e_invalida_o_cache(self):
        from articles.services import cache

        self._cadastrar()
        self._requisicao('GET', f'/articles/{self.article_id}/')  # enche o cache
        self.assertEqual(cache.get_client().exists(f'artigo:{self.article_id}'), 1)

        self._json('PUT', f'/articles/{self.article_id}/', {
            'title': self.titulo, 'authors': ['Ana', 'Bruno'], 'area': 'Computação',
        })
        self.assertEqual(cache.get_client().exists(f'artigo:{self.article_id}'), 0)
        self.assertEqual(self._acoes_no_dynamodb(), ['CREATE', 'UPDATE'])

    def test_download_devolve_o_pdf_enviado(self):
        self._cadastrar()
        _, dados = self._requisicao('GET', f'/articles/{self.article_id}/download/')
        with urllib.request.urlopen(dados['download_url'], timeout=30) as resposta:
            conteudo = resposta.read()
        self.assertEqual(conteudo, (PDFS / 'artigo_nuvem.pdf').read_bytes())

    def test_arquivo_que_nao_e_pdf_e_recusado(self):
        limite = uuid.uuid4().hex
        corpo = b''.join(
            f'--{limite}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode()
            for n, v in {'title': self.titulo, 'authors': '["Ana"]', 'area': 'Computação'}.items()
        ) + (
            f'--{limite}\r\nContent-Disposition: form-data; name="file"; filename="x.txt"\r\n'
            'Content-Type: text/plain\r\n\r\ntexto\r\n'
            f'--{limite}--\r\n'
        ).encode()
        with self.assertRaises(urllib.error.HTTPError) as erro:
            self._requisicao('POST', '/articles/', corpo, {'Content-Type': f'multipart/form-data; boundary={limite}'})
        self.assertEqual(erro.exception.code, 415)

    def test_delete_remove_registro_pdf_e_loga(self):
        from botocore.exceptions import ClientError

        from articles.services.aws import client

        self._cadastrar()
        self._requisicao('DELETE', f'/articles/{self.article_id}/')
        with self.assertRaises(urllib.error.HTTPError) as erro:
            self._requisicao('GET', f'/articles/{self.article_id}/')
        self.assertEqual(erro.exception.code, 404)
        with self.assertRaises(ClientError):
            client('s3').head_object(Bucket=os.environ['S3_BUCKET'], Key=f'artigos/{self.article_id}.pdf')
        self.assertIn('DELETE', self._acoes_no_dynamodb())
        self.article_id = None
