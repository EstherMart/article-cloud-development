# 5. ElastiCache Redis

[← 4. DynamoDB](04-dynamodb.md) | [Índice](README.md) | [6. SNS e SQS →](06-sns-sqs.md)

## O que é o ElastiCache
É um Redis gerenciado: um banco que vive **na memória**. Ele guarda cópias temporárias das consultas, para a API não ir ao RDS toda vez. Memória é cara, então ele nunca guarda PDF.

Caminho: ElastiCache > **Caches Redis OSS** (ou **Criar cache**).

Os nomes abaixo seguem o console em português. Entre parênteses vai o nome em inglês, caso o seu console esteja em outro idioma. Campo que não aparece aqui fica no valor padrão.

| Campo (inglês) | Valor | O que é e por quê |
|---|---|---|
| Mecanismo (Engine) | **Redis OSS** | O que o código usa (biblioteca `redis`) |
| Opções de implantação (Deployment option) | **Projete seu próprio cache** (Design your own cache) | Permite escolher o tamanho e o custo |
| Método de criação | **Cache de cluster** (Cluster cache, baseado em nós) | Evite o "Serverless": tem custo mínimo mesmo sem uso |
| Modo cluster (Cluster mode) | **Desabilitado** | Um só nó. Basta para o laboratório |
| Nome (Name) | `artigos-redis` | Rótulo |
| Versão do mecanismo | a padrão sugerida | Sem ajustes |
| Porta (Port) | `6379` | A porta padrão do Redis |
| Tipo de nó (Node type) | `cache.t3.micro` | O menor e mais barato |
| Número de réplicas (Replicas) | `0` | Cada réplica soma custo |
| Multi-AZ | **desligado** | Exige réplica |
| Grupo de sub-redes (Subnet group) | criar novo, VPC padrão, sub-redes padrão | Em quais sub-redes o cache fica |
| Grupos de segurança (Security groups) | `sg-redis`. Remova o `default` | O firewall do cache ([seção 0](00-preparacao.md)) |
| Criptografia em repouso (At-rest encryption) | desligada (ou padrão) | Sem custo, opcional |
| Criptografia em trânsito (In-transit encryption) | **desligada** | Permite usar `redis://` simples. Com ela ligada, a URL seria `rediss://` |
| Controle de acesso (Access control) | **Sem controle de acesso** (No access control) | A proteção vem da rede (`sg-redis`) |
| Backup > Backups automáticos | **desligado** | Cache é descartável |

Clique em **Criar**. Espere **Disponível**. Copie o **Ponto de extremidade primário** (Primary endpoint), sem a porta. No `.env`: `REDIS_URL=redis://<endpoint>:6379/0`.

## Como o código usa o Redis (`backend/articles/services/cache.py`)
- `get_client()`: `redis.Redis.from_url(REDIS_URL)` com timeouts de 2 s (conexão e leitura), para que um endpoint errado não trave a API.
- `get_or_set(key, loader, ttl=300)`: padrão cache-aside com JSON.
- `invalidate_article(id)`: apaga `artigo:{id}`, `artigos:recentes` e `busca:*` (use `scan_iter`, nunca `KEYS`).
- Se o Redis falhar, chame o `loader` direto. O cache nunca derruba a API.
- Nunca guarde PDF no Redis.

### O que pode dar errado
| Sintoma | Causa provável |
|---|---|
| API lenta, cada requisição demora ~2 s ou mais | Endpoint errado ou `sg-redis` sem a regra do `sg-api`: cada leitura espera o timeout e cai no RDS. O log mostra `Redis não conseguiu ler` |
| API funciona, mas `keys 'artigo:*'` vem vazio | `REDIS_URL` vazio (usa `127.0.0.1`) ou apontando para outro cache |
| `Connection reset` ou erro de protocolo | Criptografia em trânsito ligada. O código usa `redis://`; com ela ligada, seria `rediss://` |
| O worker não derruba o cache | O worker precisa de `REDIS_URL` e do `sg-worker` liberado no `sg-redis` (6379). Se falhar, só grava no log e o cache expira em 5 minutos |

## Testar
O Redis só é acessível de dentro da VPC. Teste pela EC2 da API ([etapa 2](02-ec2-api.md)):
1. `sudo dnf install -y redis6` (ou `redis`) para ter o `redis-cli`.
2. `redis-cli -h <endpoint> ping`. Deve responder `PONG`.
3. `redis-cli -h <endpoint> set teste 1 EX 60` e depois `get teste`.
4. Depois de implementar: chame `GET /articles/1/` duas vezes. Em `redis-cli`, `keys 'artigo:*'` deve listar a chave. Faça um `PUT` e confirme que a chave some.

No console: ElastiCache > cluster > **Monitoring**. **CacheHits** e **CacheMisses** sobem com as chamadas.

## Apagar
ElastiCache > **Caches Redis OSS** > selecione > **Ações > Excluir**. Recuse o backup final.

## Por que configuramos assim (estudo para a arguição)

| Configuração | Motivo |
|---|---|
| Cache-aside | A API consulta o Redis. Se não achar, consulta o RDS e grava no Redis |
| TTL de 5 minutos | Rede de segurança: o dado velho some sozinho se a invalidação falhar |
| Invalidar em CREATE, UPDATE e DELETE | O usuário não vê dado desatualizado |
| O worker invalida `artigo:{id}` | A tradução muda o dado. O cache precisa acompanhar |
| Só metadados, listas e buscas | PDF tem vários MB e a memória do Redis é cara |
| `sg-redis` só do `sg-api` | O Redis não tem senha por padrão. A rede o protege |
| Redis fora do ar não derruba a API | O cache é otimização. Sem ele, a API usa só o RDS |
| `scan_iter` em vez de `KEYS` | `KEYS` bloqueia o Redis inteiro em bases grandes |
| 0 réplicas, `cache.t3.micro` | Custo mínimo no laboratório |

Pergunta provável: "Como evita dado desatualizado?" Com TTL curto e invalidação a cada escrita (inclusive a do worker).

---
[← 4. DynamoDB](04-dynamodb.md) | [Índice](README.md) | [6. SNS e SQS →](06-sns-sqs.md)
