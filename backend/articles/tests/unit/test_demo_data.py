from importlib import import_module

from django.apps import apps
from django.test import TestCase, override_settings

from articles.demo.artigos import ARTIGOS
from articles.models import Article

migration = import_module('articles.migrations.0005_artigos_de_demonstracao')


@override_settings(SEED_DEMO_DATA=True)
class DemoDataTests(TestCase):
    """A migration de demonstração deixa artigos prontos para a busca da arguição."""

    def test_cria_os_artigos_uma_unica_vez_e_a_busca_os_encontra(self):
        migration.criar_artigos(apps, None)
        migration.criar_artigos(apps, None)  # repetir não duplica
        self.assertEqual(Article.objects.count(), len(ARTIGOS))

        resposta = self.client.get('/articles/search/', {'q': 'Ana Souza'})
        self.assertEqual(len(resposta.json()), 4)
        self.assertFalse(Article.objects.exclude(processing_status='PROCESSADO').exists())
        self.assertFalse(Article.objects.filter(translated_abstract='').exists())
