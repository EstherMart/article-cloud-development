"""ElastiCache Redis (requisito 4).

Só roda de uma EC2 na mesma VPC: o Redis não é acessível de fora.
As chaves de teste usam o prefixo `teste-integracao:` e são apagadas no fim.
"""
import os
import time
import uuid
from unittest import mock

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

    def test_endpoint_inalcancavel_responde_rapido_e_cai_no_loader(self):
        # Usa o get_client de verdade, com os timeouts de produção (2 s). 10.255.255.1 não responde.
        with mock.patch.dict(os.environ, {'REDIS_URL': 'redis://10.255.255.1:6379/0'}), \
                mock.patch.object(self.cache, 'REDIS_CLIENT', None):
            inicio = time.time()
            resultado = self.cache.get_or_set(self.chave, lambda: {'veio': 'do-rds'})
            duracao = time.time() - inicio
        self.assertEqual(resultado, {'veio': 'do-rds'})
        self.assertLess(duracao, 8, 'o cliente Redis não tem timeout: um endpoint errado trava a API')
