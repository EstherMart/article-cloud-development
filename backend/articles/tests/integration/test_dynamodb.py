"""DynamoDB (requisito 5). Usa o dynamo_log do projeto contra a tabela real.

A chave da tabela tem de ser a que o código grava: `article_id` String (partição) e `timestamp`
String (ordenação). Com outro tipo, toda gravação falha e o `log_action` engole o erro, então a
API continua funcionando sem gravar log nenhum. Estes testes pegam isso. Apagam o que criam.
"""
import os
from unittest import mock

from .base import AwsIntegrationTestCase, novo_article_id

ARTIGO = {
    'id': 1,
    'title': 'Artigo de teste',
    'area': 'Computação',
    'authors': ['Ana', 'Bruno'],
    'tags': ['AWS'],
    'abstract': '',
    'processing_status': 'PENDENTE',
    'upload_datetime': '2026-10-11T12:00:00+00:00',
}


class DynamoLogTests(AwsIntegrationTestCase):
    REQUIRED_ENV = ('DYNAMODB_TABLE',)

    def setUp(self):
        from articles.services import dynamo_log
        from articles.services.aws import resource

        self.log = dynamo_log
        self.table = resource('dynamodb').Table(os.environ['DYNAMODB_TABLE'])
        self.article_id = novo_article_id()
        self.addCleanup(self._limpar)

    def _itens(self):
        from boto3.dynamodb.conditions import Key

        resposta = self.table.query(KeyConditionExpression=Key('article_id').eq(str(self.article_id)))
        return resposta['Items']

    def _limpar(self):
        for item in self._itens():
            self.table.delete_item(Key={'article_id': item['article_id'], 'timestamp': item['timestamp']})

    def test_chave_da_tabela_e_a_que_o_codigo_grava(self):
        chaves = {k['KeyType']: k['AttributeName'] for k in self.table.key_schema}
        tipos = {a['AttributeName']: a['AttributeType'] for a in self.table.attribute_definitions}
        self.assertEqual(chaves, {'HASH': 'article_id', 'RANGE': 'timestamp'})
        self.assertEqual(tipos, {'article_id': 'S', 'timestamp': 'S'})

    def test_grava_acao_dados_e_hora(self):
        self.log.log_action('CREATE', self.article_id, ARTIGO)
        itens = self._itens()
        self.assertEqual(len(itens), 1, 'nada foi gravado: veja o log da API (a falha de log é silenciosa)')
        item = itens[0]
        self.assertEqual(item['action'], 'CREATE')
        self.assertEqual(item['data']['title'], 'Artigo de teste')
        self.assertEqual(item['data']['authors'], ['Ana', 'Bruno'])
        self.assertIn('timestamp', item)

    def test_historico_fica_em_ordem_cronologica(self):
        for acao in ('CREATE', 'UPDATE', 'DELETE'):
            self.log.log_action(acao, self.article_id, ARTIGO)
        self.assertEqual([i['action'] for i in self._itens()], ['CREATE', 'UPDATE', 'DELETE'])

    def test_falha_de_log_nao_levanta_excecao(self):
        # A decisão do grupo: o CRUD nunca cai por causa do log.
        with mock.patch('articles.services.dynamo_log.settings.AWS_DYNAMODB_TABLE_NAME', 'tabela-que-nao-existe'):
            self.log.log_action('CREATE', self.article_id, ARTIGO)
        self.assertEqual(self._itens(), [])
