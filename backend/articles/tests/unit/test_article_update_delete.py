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

    def test_campos_ausentes_retornam_400(self):
        article_id = self.create_article()
        self.assertEqual(self.send('put', f'/articles/{article_id}/', {}).status_code, 400)

    def test_id_inexistente_retorna_404(self):
        body = {'title': 'x', 'authors': ['y'], 'area': 'z'}
        self.assertEqual(self.send('put', '/articles/999/', body).status_code, 404)

    def test_json_invalido_retorna_400(self):
        article_id = self.create_article()
        resp = self.client.put(f'/articles/{article_id}/', data='{nao e json', content_type='application/json')
        self.assertEqual(resp.status_code, 400)


class ArticleDeleteTests(ApiTestCase):
    """DELETE /articles/<id>/"""

    def test_remove_o_artigo(self):
        article_id = self.create_article()
        self.assertEqual(self.client.delete(f'/articles/{article_id}/').status_code, 200)
        self.assertFalse(Article.objects.filter(id=article_id).exists())

    def test_id_inexistente_retorna_404(self):
        self.assertEqual(self.client.delete('/articles/999/').status_code, 404)
