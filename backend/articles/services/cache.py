"""Cache Redis (ElastiCache). Branch: feat/cache-redis.

Padrão cache-aside:
    1. procura a chave no Redis;
    2. hit: devolve; miss: consulta o RDS, grava com TTL e devolve.

Regras:
- Só metadados, listas e buscas. NUNCA o PDF.
- TTL de 5 a 10 minutos (CACHE_TTL), como rede de segurança.
- Todo CREATE, UPDATE e DELETE invalida as chaves afetadas.
- O worker também invalida artigo:{id} depois de gravar a tradução.
- Valores guardados como JSON (json.dumps / json.loads).

Chaves:
    artigo:{id}        detalhe de um artigo
    artigos:recentes   lista dos mais recentes
    busca:{termos}     resultado de uma busca (invalidar com o padrão busca:*)
"""
CACHE_TTL = 300  # segundos


def get_client():
    """Conexão com o Redis a partir de REDIS_URL (redis.Redis.from_url).

    Crie uma vez por processo. Não guarde estado de aplicação em memória local:
    a API roda em várias instâncias no Auto Scaling.
    """
    raise NotImplementedError


def get_or_set(key, loader, ttl=CACHE_TTL):
    """Cache-aside. `loader` é uma função sem argumentos que consulta o RDS.

    Se o Redis estiver fora do ar, chame o loader direto: o cache nunca deve
    derrubar a API.
    """
    raise NotImplementedError


def invalidate_article(article_id):
    """Apaga artigo:{id}, artigos:recentes e as chaves busca:*.

    Para busca:* use scan_iter(match='busca:*') e delete. Evite KEYS em produção.
    """
    raise NotImplementedError
