"""DynamoDB (requisito 5). Variável: DYNAMODB_TABLE. Depende de services/dynamo_log.py.

O que vai aqui:

# class DynamoLogTests(AwsIntegrationTestCase):
#     @require_env('DYNAMODB_TABLE')
#     def test_log_action_grava_acao_dados_e_hora(self):
#         # log_action('CREATE', id_de_teste, {...}); query por article_id encontra o item
#         # com action, data e timestamp (os três campos que a spec exige).
#
#     def test_historico_fica_ordenado_por_timestamp(self):
#         # dois logs do mesmo artigo voltam em ordem cronológica.
#
#     def test_log_sobrevive_ao_delete_do_artigo(self):
#         # log DELETE continua na tabela (auditoria).
#
#     def test_aceita_dados_com_numeros_decimais(self):
#         # float vira Decimal ou str sem erro de serialização.
#
# Limpeza: delete_item de cada item criado (addCleanup).
# Pega: tabela com nome ou chave diferente do código, permissão da LabRole.
"""
