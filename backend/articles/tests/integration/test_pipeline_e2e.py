"""Fluxo completo com todos os serviços. É o último teste: rode depois dos outros passarem.

Requisitos para rodar:
- API no ar (API_BASE_URL, ex.: http://<ip-da-ec2>:8000) e usuário E2E_USERNAME criado.
- Worker rodando.
- .env com S3_BUCKET, DYNAMODB_TABLE e REDIS_URL (de dentro da EC2).

ATENÇÃO: o POST com PDF ainda não existe. Os campos do multipart abaixo (title, authors, area,
user, abstract, file) são a proposta. Ajuste _cadastrar quando o upload for implementado.
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
        self.usuario = os.environ.get('E2E_USERNAME', 'teste')
        self.titulo = f'Artigo e2e {uuid.uuid4().hex[:8]}'
        self.article_id = None
        self.addCleanup(self._apagar)

    def _requisicao(self, metodo, caminho, corpo=None, headers=None):
        req = urllib.request.Request(self.api + caminho, data=corpo, method=metodo, headers=headers or {})
        with urllib.request.urlopen(req, timeout=30) as resposta:
            return resposta.status, json.loads(resposta.read() or b'null')

    def _cadastrar(self):
        limite = uuid.uuid4().hex
        campos = {
            'title': self.titulo, 'authors': 'Ana', 'area': 'Computação',
            'user': self.usuario, 'abstract': 'Resumo digitado para o teste de ponta a ponta.',
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

    def _esperar_processado(self, limite=90):
        fim = time.time() + limite
        while time.time() < fim:
            _, artigo = self._requisicao('GET', f'/articles/{self.article_id}/')
            if artigo['processing_status'] == 'PROCESSADO':
                return artigo
            time.sleep(3)
        self.fail('o worker não processou o artigo a tempo: confira o worker e a fila')

    def test_cadastro_ate_processado(self):
        from articles.services.aws import client, resource

        artigo = self._cadastrar()
        self.assertEqual(artigo['processing_status'], 'PENDENTE')  # 1. RDS

        client('s3').head_object(Bucket=os.environ['S3_BUCKET'], Key=f'artigos/{self.article_id}.pdf')  # 2. S3

        tabela = resource('dynamodb').Table(os.environ['DYNAMODB_TABLE'])  # 3. DynamoDB
        itens = tabela.scan()['Items']
        self.assertTrue(
            any(str(i.get('article_id')) == str(self.article_id) and i.get('action') == 'CREATE' for i in itens)
        )

        self._esperar_processado()  # 4. SNS, SQS, worker e RDS

        from articles.services import cache  # 5. Redis: a 2ª leitura vem do cache
        self._requisicao('GET', f'/articles/{self.article_id}/')
        self._requisicao('GET', f'/articles/{self.article_id}/')
        self.assertEqual(cache.get_client().exists(f'artigo:{self.article_id}'), 1)

    def test_delete_remove_registro_e_pdf(self):
        from botocore.exceptions import ClientError

        from articles.services.aws import client

        self._cadastrar()
        self._requisicao('DELETE', f'/articles/{self.article_id}/')
        with self.assertRaises(urllib.error.HTTPError) as erro:
            self._requisicao('GET', f'/articles/{self.article_id}/')
        self.assertEqual(erro.exception.code, 404)
        with self.assertRaises(ClientError):
            client('s3').head_object(Bucket=os.environ['S3_BUCKET'], Key=f'artigos/{self.article_id}.pdf')
        self.article_id = None
