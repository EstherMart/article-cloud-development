from .base import ApiTestCase


class ArticleDetailTests(ApiTestCase):
    """GET /articles/<id>/"""


    def test_id_inexistente_retorna_404(self):
        self.assertEqual(self.client.get('/articles/999/').status_code, 404)
