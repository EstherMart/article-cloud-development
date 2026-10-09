"""SNS e SQS (requisito 6). Variáveis: SNS_TOPIC_ARN, SQS_QUEUE_URL. Depende de services/messaging.py.

O que vai aqui:

# class SnsSqsTests(AwsIntegrationTestCase):
#     @require_env('SNS_TOPIC_ARN', 'SQS_QUEUE_URL')
#     def test_publicacao_chega_na_fila_com_raw_delivery(self):
#         # publish_article_created(...); receive_message (long polling) recebe;
#         # json.loads(Body) já é {"article_id", "s3_key", "bucket"} (sem envelope do SNS).
#         # delete_message no fim.
#
#     def test_mensagem_nao_apagada_volta_apos_visibility_timeout(self):
#         # recebe sem apagar; depois do timeout, a mesma mensagem volta (ReceiveCount 2).
#
#     def test_mensagem_vai_para_a_dlq_apos_3_tentativas(self):
#         # recebe 3 vezes sem apagar; a DLQ passa a ter a mensagem. Lento: marcar como teste longo.
#
# Limpeza: purge da fila só se ela for exclusiva de teste. Nunca purgar a fila real.
# Pega: assinatura SNS->SQS faltando, política da fila sem permissão, raw delivery desligado.
"""
