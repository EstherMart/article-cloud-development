"""ElastiCache Redis (requisito 4). Depende de articles/services/cache.py implementado.

Só roda de uma EC2 na mesma VPC: o Redis não é acessível de fora.
As chaves de teste usam o prefixo `teste-integracao:` e são apagadas no fim.
"""
import uuid

from .base import AwsIntegrationTestCase, novo_article_id


class RedisCacheTests(AwsIntegrationTestCase):
    REQUIRED_ENV = ('REDIS_URL',)

    def setUp(self):
        from articles.services import cache

        self.cache = cache
        self.redis = cache.get_client()
        self.chave = f'teste-integracao:{uuid.uuid4()}'
        self.addCleanup(self.redis.delete, self.chave)

    def test_ping(self):
        self.assertTrue(self.redis.ping())

    def test_get_or_set_chama_o_loader_so_uma_vez(self):
        chamadas = []

        def loader():
            chamadas.append(1)
            return {'id': 1, 'title': 'Artigo'}

        primeiro = self.cache.get_or_set(self.chave, loader)
        segundo = self.cache.get_or_set(self.chave, loader)
        self.assertEqual(primeiro, segundo)
        self.assertEqual(len(chamadas), 1, 'a segunda chamada deveria vir do cache')

    def test_ttl_e_aplicado(self):
        self.cache.get_or_set(self.chave, lambda: {'ok': True}, ttl=30)
        self.assertTrue(0 < self.redis.ttl(self.chave) <= 30)

    def test_invalidate_article_apaga_as_chaves_afetadas(self):
        article_id = novo_article_id()
        chaves = [f'artigo:{article_id}', 'artigos:recentes', f'busca:teste-{article_id}']
        for chave in chaves:
            self.redis.set(chave, '{}')
        self.cache.invalidate_article(article_id)
        for chave in chaves:
            self.assertEqual(self.redis.exists(chave), 0, chave)

    def test_redis_fora_do_ar_nao_derruba_a_api(self):
        import redis
        from unittest import mock

        morto = redis.Redis.from_url('redis://127.0.0.1:1/0', socket_connect_timeout=1, socket_timeout=1)
        with mock.patch.object(self.cache, 'get_client', return_value=morto):
            self.assertEqual(self.cache.get_or_set(self.chave, lambda: {'veio': 'do-rds'}), {'veio': 'do-rds'})
