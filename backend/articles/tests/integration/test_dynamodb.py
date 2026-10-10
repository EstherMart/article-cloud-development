"""DynamoDB (requisito 5). Depende de articles/services/dynamo_log.py implementado.

O tipo da chave `article_id` (Number ou String) e o nome da chave de ordenação são lidos da
própria tabela, então o teste vale para a decisão que o grupo tomar. Apaga o que criou.
"""
import os

from .base import AwsIntegrationTestCase, novo_article_id


class DynamoLogTests(AwsIntegrationTestCase):
    REQUIRED_ENV = ('DYNAMODB_TABLE',)

    def setUp(self):
        from articles.services import dynamo_log
        from articles.services.aws import resource

        self.log = dynamo_log
        self.table = resource('dynamodb').Table(os.environ['DYNAMODB_TABLE'])
        chaves = {k['KeyType']: k['AttributeName'] for k in self.table.key_schema}
        self.pk, self.sk = chaves['HASH'], chaves.get('RANGE')
        tipos = {a['AttributeName']: a['AttributeType'] for a in self.table.attribute_definitions}
        self.pk_e_numero = tipos[self.pk] == 'N'
        self.article_id = novo_article_id()
        self.addCleanup(self._limpar)

    def _valor_pk(self):
        return self.article_id if self.pk_e_numero else str(self.article_id)

    def _itens(self):
        from boto3.dynamodb.conditions import Key

        resposta = self.table.query(KeyConditionExpression=Key(self.pk).eq(self._valor_pk()))
        return resposta['Items']

    def _limpar(self):
        for item in self._itens():
            chave = {self.pk: item[self.pk]}
            if self.sk:
                chave[self.sk] = item[self.sk]
            self.table.delete_item(Key=chave)

    def test_grava_acao_dados_e_hora(self):
        self.log.log_action('CREATE', self.article_id, {'title': 'Artigo de teste', 'area': 'Computação'})
        itens = self._itens()
        self.assertEqual(len(itens), 1)
        item = itens[0]
        self.assertEqual(item['action'], 'CREATE')
        self.assertEqual(item['data']['title'], 'Artigo de teste')
        self.assertIn('timestamp', item)

    def test_historico_fica_em_ordem_cronologica(self):
        for acao in ('CREATE', 'UPDATE', 'DELETE'):
            self.log.log_action(acao, self.article_id, {'passo': acao})
        self.assertEqual([i['action'] for i in self._itens()], ['CREATE', 'UPDATE', 'DELETE'])

    def test_log_de_delete_e_gravado(self):
        # O log continua existindo mesmo depois de o artigo sumir do RDS (auditoria).
        self.log.log_action('DELETE', self.article_id, {'title': 'Artigo apagado'})
        self.assertEqual(self._itens()[0]['action'], 'DELETE')

    def test_aceita_dados_com_numero_decimal(self):
        # O DynamoDB rejeita float. O serviço precisa converter.
        self.log.log_action('UPDATE', self.article_id, {'nota': 4.5})
        self.assertEqual(len(self._itens()), 1)
