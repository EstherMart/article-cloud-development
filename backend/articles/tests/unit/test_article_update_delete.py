from django.contrib.auth.models import User

from articles.models import Article

from .base import ApiTestCase


class ArticleUpdateTests(ApiTestCase):
    """PUT /articles/<id>/"""

    def test_atualiza_titulo_autores_e_area(self):
        article_id = self.create_article()
        body = {'title': 'Novo título', 'authors': ['Carla'], 'area': 'Redes'}
        resp = self.send('put', f'/articles/{article_id}/', body)
        self.assertEqual(resp.status_code, 200)
        article = Article.objects.get(id=article_id)
        self.assertEqual(article.title, 'Novo título')
        self.assertEqual(article.area, 'Redes')
        self.assertEqual([a.name for a in article.authors.all()], ['Carla'])


    def test_titulo_duplicado_retorna_409(self):
        self.create_article()
        outro = self.create_article(title='Outro artigo')
        body = {'title': 'Introdução à Nuvem', 'authors': ['Ana'], 'area': 'Redes'}
        self.assertEqual(self.send('put', f'/articles/{outro}/', body).status_code, 409)


    def test_artigo_de_outro_usuario_retorna_403(self):
        article_id = self.create_article()
        self.login_as(User.objects.create_user(username='outro', password='senha-forte-123'))
        body = {'title': 'x', 'authors': ['y'], 'area': 'z'}
        self.assertEqual(self.send('put', f'/articles/{article_id}/', body).status_code, 403)
        self.assertEqual(Article.objects.get(id=article_id).title, 'Introdução à Nuvem')


class ArticleDeleteTests(ApiTestCase):
    """DELETE /articles/<id>/"""

    def test_remove_o_artigo(self):
        article_id = self.create_article()
        self.assertEqual(self.client.delete(f'/articles/{article_id}/').status_code, 200)
        self.assertFalse(Article.objects.filter(id=article_id).exists())

    def test_apaga_o_pdf_do_s3(self):
        article_id = self.create_article()
        self.client.delete(f'/articles/{article_id}/')
        self.s3.delete_object.assert_called_once()


    def test_artigo_de_outro_usuario_retorna_403(self):
        article_id = self.create_article()
        self.login_as(User.objects.create_user(username='outro', password='senha-forte-123'))
        self.assertEqual(self.client.delete(f'/articles/{article_id}/').status_code, 403)
        self.assertTrue(Article.objects.filter(id=article_id).exists())
