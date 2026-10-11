"""S3 (requisito 3).

Usa ids de teste (900000000 em diante) e apaga o objeto no fim.
"""
import time
import urllib.error
import urllib.request

from .base import PDFS, AwsIntegrationTestCase, novo_article_id


class S3Tests(AwsIntegrationTestCase):
    REQUIRED_ENV = ('S3_BUCKET',)

    def setUp(self):
        from articles.services import s3

        self.s3 = s3
        self.article_id = novo_article_id()
        self.pdf = (PDFS / 'artigo_nuvem.pdf').read_bytes()
        self.key = f'artigos/{self.article_id}.pdf'
        self.addCleanup(self._limpar)

    def _limpar(self):
        try:
            self.s3.delete_pdf(self.key)
        except Exception:
            pass

    def _upload(self):
        with open(PDFS / 'artigo_nuvem.pdf', 'rb') as arquivo:
            return self.s3.upload_pdf(self.article_id, arquivo)

    def _baixar(self, url):
        with urllib.request.urlopen(url, timeout=15) as resposta:
            return resposta.read()

    def test_upload_devolve_a_chave_padrao(self):
        self.assertEqual(self._upload(), self.key)

    def test_baixa_o_mesmo_conteudo_pela_url_pre_assinada(self):
        self._upload()
        self.assertEqual(self._baixar(self.s3.presigned_url(self.key)), self.pdf)

    def test_objeto_fica_com_content_type_pdf(self):
        import os

        from articles.services.aws import client

        self._upload()
        head = client('s3').head_object(Bucket=os.environ['S3_BUCKET'], Key=self.key)
        self.assertEqual(head['ContentType'], 'application/pdf')

    def test_bucket_e_privado(self):
        import os

        self._upload()
        url_sem_assinatura = f"https://{os.environ['S3_BUCKET']}.s3.amazonaws.com/{self.key}"
        with self.assertRaises(urllib.error.HTTPError) as erro:
            self._baixar(url_sem_assinatura)
        self.assertEqual(erro.exception.code, 403)

    def test_url_pre_assinada_expira(self):
        self._upload()
        url = self.s3.presigned_url(self.key, expires_in=1)
        time.sleep(3)
        with self.assertRaises(urllib.error.HTTPError) as erro:
            self._baixar(url)
        self.assertEqual(erro.exception.code, 403)

    def test_delete_remove_o_objeto(self):
        import os

        from botocore.exceptions import ClientError

        from articles.services.aws import client

        self._upload()
        self.s3.delete_pdf(self.key)
        with self.assertRaises(ClientError) as erro:
            client('s3').head_object(Bucket=os.environ['S3_BUCKET'], Key=self.key)
        self.assertEqual(erro.exception.response['Error']['Code'], '404')
