"""ElastiCache Redis (requisito 4). Variável: REDIS_URL. Depende de services/cache.py.
Só roda de uma EC2 na mesma VPC: o Redis não é acessível de fora.

O que vai aqui:

# class RedisCacheTests(AwsIntegrationTestCase):
#     @require_env('REDIS_URL')
#     def test_ping(self):
#         # get_client().ping() é True.
#
#     def test_get_or_set_chama_o_loader_uma_vez(self):
#         # 1ª chamada: miss, executa o loader e grava; 2ª: hit, loader não roda.
#
#     def test_ttl_e_aplicado(self):
#         # ttl(chave) fica entre 1 e CACHE_TTL.
#
#     def test_invalidate_article_apaga_as_chaves(self):
#         # artigo:{id}, artigos:recentes e busca:* somem.
#
#     def test_redis_fora_do_ar_nao_derruba(self):
#         # com REDIS_URL apontando para porta fechada, get_or_set devolve o valor do loader.
#
# Limpeza: delete das chaves com prefixo de teste.
# Pega: Security Group 6379 fechado, endpoint errado, TLS ligado com redis:// simples.
"""
