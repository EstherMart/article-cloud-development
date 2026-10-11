from django.contrib.auth.models import User
from botocore.exceptions import BotoCoreError
from django.core.files.uploadedfile import SimpleUploadedFile
import json

from articles.models import Article, Author, Tag
from django.conf import settings

from .base import ApiTestCase


class ArticleCreateTests(ApiTestCase):
    """POST /articles/"""

    def test_cria_artigo_pendente(self):
        resp = self.post_article()
        self.assertEqual(resp.status_code, 201)
        article = resp.json()['article']
        self.assertEqual(article['processing_status'], 'PENDENTE')
        self.assertEqual(sorted(article['authors']), ['Ana', 'Bruno'])
        self.assertEqual(sorted(article['tags']), ['AWS', 'Python'])

    def test_persiste_no_banco(self):
        self.post_article()
        self.assertEqual(Article.objects.count(), 1)

    def test_reaproveita_tag_existente(self):
        self.post_article()
        self.post_article(title='Segundo')
        self.assertEqual(Tag.objects.count(), 2)

    def test_campo_obrigatorio_ausente_retorna_400(self):
        for campo in ('title', 'authors', 'area'):
            with self.subTest(campo=campo):
                self.assertEqual(self.post_article(**{campo: ''}).status_code, 400)

    def test_sem_token_retorna_401(self):
        self.logout()
        self.assertEqual(self.post_article().status_code, 401)
        self.assertEqual(Article.objects.count(), 0)

    def test_artigo_pertence_ao_usuario_do_token(self):
        self.assertEqual(self.post_article().json()['article']['user'], self.USERNAME)

    def test_sem_pdf_retorna_400(self):
        self.assertEqual(self.post_article(file=None).status_code, 400)
        self.assertEqual(Article.objects.count(), 0)

    def test_envia_o_pdf_ao_s3(self):
        article = self.post_article().json()['article']
        self.s3.upload_fileobj.assert_called_once()
        self.assertEqual(
            Article.objects.get(id=article['id']).s3_key,
            f"artigos/{article['id']}.pdf",
        )

    def test_publica_evento_sns_depois_de_salvar_artigo_e_pdf(self):
        response = self.post_article(abstract='Resumo de teste')
        article = response.json()['article']

        self.assertEqual(response.status_code, 201)
        self.sns.publish.assert_called_once()
        kwargs = self.sns.publish.call_args.kwargs
        self.assertEqual(kwargs['TopicArn'], 'arn:aws:sns:us-east-1:123456789012:artigos')
        event = json.loads(kwargs['Message'])
        self.assertEqual(event['article_id'], article['id'])
        self.assertEqual(event['s3_key'], Article.objects.get(id=article['id']).s3_key)
        self.assertEqual(event['bucket'], settings.AWS_STORAGE_BUCKET_NAME)
        self.assertEqual(event['event'], 'ARTICLE_CREATED')

    def test_falha_ao_publicar_marca_artigo_como_erro_e_nao_retorna_sucesso(self):
        self.sns.publish.side_effect = RuntimeError('SNS indisponível')

        response = self.post_article()

        self.assertEqual(response.status_code, 503)
        self.assertIn('erro', response.json())
        article = Article.objects.get()
        self.assertEqual(article.processing_status, Article.ProcessingStatus.ERRO)

    def test_titulo_duplicado_retorna_409(self):
        self.post_article()
        self.assertEqual(self.post_article().status_code, 409)
        self.assertEqual(Article.objects.count(), 1)

    def test_titulo_duplicado_nao_deixa_autor_orfao(self):
        self.post_article()
        self.post_article(authors=['Autor novo'])
        self.assertFalse(Author.objects.filter(name='Autor novo').exists())

    def test_autores_deve_ser_lista(self):
        self.assertEqual(self.post_article(authors='Ana').status_code, 400)

    def test_tags_deve_ser_lista(self):
        self.assertEqual(self.post_article(tags='AWS').status_code, 400)

    def test_autores_com_json_invalido_retorna_400(self):
        self.assertEqual(self.post_article(authors='{nao e json').status_code, 400)

    def test_ignora_nomes_repetidos_e_vazios(self):
        resp = self.post_article(authors=['Ana', ' Ana ', ''], tags=['AWS', 'AWS'])
        article = resp.json()['article']
        self.assertEqual(article['authors'], ['Ana'])
        self.assertEqual(article['tags'], ['AWS'])

    def test_guarda_o_resumo_digitado(self):
        article = self.post_article(abstract='Resumo do trabalho').json()['article']
        self.assertEqual(article['abstract'], 'Resumo do trabalho')

    def test_arquivo_que_nao_e_pdf_retorna_415(self):
        file = SimpleUploadedFile('nota.txt', b'texto', content_type='text/plain')
        self.assertEqual(self.post_article(file=file).status_code, 415)
        self.s3.upload_fileobj.assert_not_called()

    def test_pdf_acima_do_limite_retorna_413(self):
        file = SimpleUploadedFile('grande.pdf', b'0' * (10 * 1024 * 1024 + 1), content_type='application/pdf')
        self.assertEqual(self.post_article(file=file).status_code, 413)

    def test_falha_do_s3_retorna_502_sem_vazar_detalhe(self):
        self.s3.upload_fileobj.side_effect = BotoCoreError()
        response = self.post_article()
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('BotoCoreError', response.json()['erro'])

    def test_503_devolve_o_id_do_artigo_salvo(self):
        self.sns.publish.side_effect = RuntimeError('SNS indisponível')
        response = self.post_article()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['article_id'], Article.objects.get().id)


class ArticleReprocessTests(ApiTestCase):
    """POST /articles/<id>/reprocess/"""

    def article_em_erro(self):
        self.sns.publish.side_effect = RuntimeError('SNS indisponível')
        article_id = self.post_article().json()['article_id']
        self.sns.publish.side_effect = None
        self.sns.publish.reset_mock()
        return article_id

    def test_reenvia_evento_e_volta_para_pendente(self):
        article_id = self.article_em_erro()
        response = self.client.post(f'/articles/{article_id}/reprocess/')
        self.assertEqual(response.status_code, 200)
        self.sns.publish.assert_called_once()
        self.assertEqual(Article.objects.get(id=article_id).processing_status, 'PENDENTE')

    def test_artigo_que_nao_esta_em_erro_retorna_409(self):
        article_id = self.create_article()
        self.assertEqual(self.client.post(f'/articles/{article_id}/reprocess/').status_code, 409)

    def test_falha_de_novo_mantem_erro_e_retorna_503(self):
        article_id = self.article_em_erro()
        self.sns.publish.side_effect = RuntimeError('SNS indisponível')
        self.assertEqual(self.client.post(f'/articles/{article_id}/reprocess/').status_code, 503)
        self.assertEqual(Article.objects.get(id=article_id).processing_status, 'ERRO')

    def test_outro_usuario_retorna_403(self):
        article_id = self.article_em_erro()
        outro = User.objects.create_user(username='outro', password='senha-forte-123')
        self.login_as(outro)
        self.assertEqual(self.client.post(f'/articles/{article_id}/reprocess/').status_code, 403)

    def test_sem_token_retorna_401(self):
        article_id = self.article_em_erro()
        self.logout()
        self.assertEqual(self.client.post(f'/articles/{article_id}/reprocess/').status_code, 401)
