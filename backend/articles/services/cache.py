"""Cache Redis, padrão cache-aside: hit devolve o JSON; miss consulta o RDS, grava com TTL e devolve.

Chaves: `artigo:{id}`, `artigos:recentes`, `busca:{termos}`. Só metadados, nunca o PDF.
"""

import os
import json
import logging
import redis

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # segundos
REDIS_CLIENT = None


def get_client():
    global REDIS_CLIENT
    if REDIS_CLIENT is None:
        url = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
        REDIS_CLIENT = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return REDIS_CLIENT


def get_or_set(key, loader, ttl=CACHE_TTL):
    client = get_client()

    try:
        cached_data = client.get(key)
        if cached_data is not None:
            return json.loads(cached_data)
    except Exception as e:
        logger.error(f"Redis não conseguiu ler {key}: {e}")

    data = loader()

    try:
        client.set(key, json.dumps(data), ex=ttl)
    except Exception as e:
        logger.error(f"Redis não conseguiu salvar a chave {key}: {e}")

    return data


def invalidate_article(article_id):
    client = get_client()

    try:
        keys = [f'artigo:{article_id}', 'artigos:recentes']
        client.delete(*keys)

        for key in client.scan_iter(match='busca:*'):
            client.delete(key)

    except Exception as e:
        logger.error(f"Erro ao invalidar cache de {article_id}: {e}")
