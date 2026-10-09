from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase

from articles.models import Article, Author, Tag


class ArticleModelTests(TestCase):
    """Regras do modelo de dados, sem passar pela API."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='teste', password='123456')

    def make_article(self, **kwargs):
        defaults = {'title': 'Artigo', 'area': 'Computação', 'user': self.user}
        defaults.update(kwargs)
        return Article.objects.create(**defaults)

    def test_status_padrao_e_pendente(self):
        self.assertEqual(self.make_article().processing_status, Article.ProcessingStatus.PENDENTE)

    def test_campos_do_worker_comecam_vazios(self):
        article = self.make_article()
        self.assertEqual(article.abstract, '')
        self.assertEqual(article.translated_abstract, '')
        self.assertEqual(article.s3_key, '')

    def test_titulo_e_unico(self):
        self.make_article(title='Repetido')
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_article(title='Repetido')

    def test_artigo_aceita_varios_autores_e_tags(self):
        article = self.make_article()
        article.authors.add(Author.objects.create(name='Ana'), Author.objects.create(name='Bruno'))
        article.tags.add(Tag.objects.create(name='AWS'))
        self.assertEqual(article.authors.count(), 2)
        self.assertEqual(article.tags.count(), 1)

    def test_nome_da_tag_e_unico(self):
        Tag.objects.create(name='AWS')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Tag.objects.create(name='AWS')

    def test_apagar_usuario_apaga_artigos(self):
        self.make_article()
        self.user.delete()
        self.assertEqual(Article.objects.count(), 0)
