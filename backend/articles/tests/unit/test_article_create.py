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
        for campo in ('title', 'authors', 'area', 'user'):
            with self.subTest(campo=campo):
                self.assertEqual(self.post_article(**{campo: ''}).status_code, 400)

    def test_usuario_inexistente_retorna_404(self):
        self.assertEqual(self.post_article(user='ninguem').status_code, 404)

    def test_json_invalido_retorna_400(self):
        resp = self.client.post('/articles/', data='{nao e json', content_type='application/json')
        self.assertEqual(resp.status_code, 400)

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

    def test_corpo_que_nao_e_objeto_retorna_400(self):
        resp = self.client.post('/articles/', data='[1, 2]', content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_ignora_nomes_repetidos_e_vazios(self):
        resp = self.post_article(authors=['Ana', ' Ana ', ''], tags=['AWS', 'AWS'])
        article = resp.json()['article']
        self.assertEqual(article['authors'], ['Ana'])
        self.assertEqual(article['tags'], ['AWS'])

    def test_guarda_o_resumo_digitado(self):
        article = self.post_article(abstract='Resumo do trabalho').json()['article']
        self.assertEqual(article['abstract'], 'Resumo do trabalho')
