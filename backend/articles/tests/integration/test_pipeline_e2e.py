"""Fluxo completo com todos os serviços. Roda da EC2, com todo o .env preenchido
e o worker ativo. É o último teste: só faz sentido depois dos outros passarem.

O que vai aqui:

# class PipelineTests(AwsIntegrationTestCase):
#     def test_cadastro_ate_processado(self):
#         # 1. POST /articles/ com PDF pequeno -> 201 e status PENDENTE (RDS).
#         # 2. objeto artigos/{id}.pdf existe no S3.
#         # 3. DynamoDB tem o log CREATE do artigo.
#         # 4. espera (polling, até ~60 s) o status virar PROCESSADO e translated_abstract preencher.
#         # 5. GET /articles/{id}/ duas vezes: a segunda vem do Redis (chave artigo:{id} existe).
#
#     def test_delete_limpa_tudo(self):
#         # DELETE remove o registro e o PDF do S3; o DynamoDB ganha o log DELETE.
#
# Limpeza: DELETE do artigo de teste no addCleanup.
"""
