from .base import ApiTestCase


class ArticleSearchTests(ApiTestCase):
    """GET /articles/search/?q="""

    def setUp(self):
        self.create_article()
        self.create_article(title='Banco de dados', authors=['Zeca'], area='Dados', tags=['SQL'])

    def search(self, termo):
        return self.client.get('/articles/search/', {'q': termo}).json()

    def test_busca_por_titulo(self):
        self.assertEqual(len(self.search('Nuvem')), 1)

    def test_busca_por_autor(self):
        self.assertEqual(len(self.search('Zeca')), 1)

    def test_busca_por_area(self):
        self.assertEqual(len(self.search('Dados')), 1)

    def test_busca_por_tag(self):
        self.assertEqual(len(self.search('SQL')), 1)

    def test_sem_resultado(self):
        self.assertEqual(self.search('inexistente'), [])

    def test_nao_duplica_quando_varias_tags_casam(self):
        self.create_article(title='Cloud', tags=['AWS', 'AWS Cloud'])
        self.assertEqual(len(self.search('Cloud')), 1)

    def test_rota_search_nao_e_confundida_com_id(self):
        self.assertEqual(self.client.get('/articles/search/').status_code, 200)
