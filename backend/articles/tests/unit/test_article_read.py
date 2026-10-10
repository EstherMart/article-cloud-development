from .base import ApiTestCase


class ArticleListTests(ApiTestCase):
    """GET /articles/"""

    def test_lista_vazia(self):
        resp = self.client.get('/articles/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_lista_todos_os_artigos(self):
        self.create_article()
        self.create_article(title='Outro artigo')
        self.assertEqual(len(self.client.get('/articles/').json()), 2)


class ArticleListQueryTests(ApiTestCase):
    """A lista não pode fazer uma consulta por artigo (N+1)."""

    def test_numero_de_consultas_nao_cresce_com_os_artigos(self):
        for i in range(5):
            self.create_article(title=f'Artigo {i}', authors=[f'Autor {i}'], tags=[f'Tag {i}'])
        with self.assertNumQueries(3):  # artigos + autores + tags
            self.client.get('/articles/')


class ArticleDetailTests(ApiTestCase):
    """GET /articles/<id>/"""

    def test_devolve_o_artigo(self):
        article_id = self.create_article()
        resp = self.client.get(f'/articles/{article_id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['title'], 'Introdução à Nuvem')

    def test_id_inexistente_retorna_404(self):
        self.assertEqual(self.client.get('/articles/999/').status_code, 404)
