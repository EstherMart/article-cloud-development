"""S3 (requisito 3). Variável: S3_BUCKET. Depende de services/s3.py implementado.

O que vai aqui:

# class S3Tests(AwsIntegrationTestCase):
#     @require_env('S3_BUCKET')
#     def test_upload_e_download_pela_url_pre_assinada(self):
#         # upload_pdf(id_de_teste, PDF pequeno) devolve a chave artigos/{id}.pdf;
#         # presigned_url(chave) baixa o mesmo conteúdo (urllib/requests).
#
#     def test_bucket_e_privado(self):
#         # GET direto na URL do objeto, sem assinatura, devolve 403.
#
#     def test_url_expira(self):
#         # presigned_url(chave, expires_in=1); espera 2 s; o GET devolve 403.
#
#     def test_delete_remove_o_objeto(self):
#         # delete_pdf(chave); head_object levanta ClientError 404.
#
# Limpeza: delete_pdf no addCleanup. Usar ids de teste (ex.: 999999).
# Pega: permissão da LabRole, nome de bucket errado, bucket público por engano.
"""
