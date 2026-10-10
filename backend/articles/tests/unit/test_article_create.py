from articles.models import Article, Author, Tag

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
        self.assertTrue(Article.objects.get(id=article['id']).s3_key.startswith(f"artigos/{article['id']}-"))

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
