# 5. DynamoDB: o serviço que continua na AWS

[← 4. Frontend e Nginx](04-frontend-nginx.md) | [Índice](README.md) | [6. CI e deploy →](06-ci-deploy.md)

A spec (item 1a) pede que a aplicação **continue** usando o banco não relacional da AWS (DynamoDB ou DocumentDB). Por isso não há container de DynamoDB no compose: o `backend` acessa a tabela real, pela internet.

## Como o backend usa

`backend/articles/services/dynamo_log.py`:

- `log_action(action, article_id, data)` faz `put_item` na tabela `DYNAMODB_TABLE` (padrão `logs_crud`).
- Item: `article_id` (String, chave de partição), `timestamp` (String ISO 8601 UTC, chave de ordenação), `action` (`CREATE`, `UPDATE` ou `DELETE`) e `data` (o artigo serializado).
- Chamado pelas views de criar, editar e excluir, **depois** de a operação principal dar certo.
- Toda exceção é capturada e registrada com `logger.exception("Não foi possível gravar o log ...")`. **Falha de log não derruba o CRUD**, mas também não aparece para o usuário: só no log do backend.
- O cliente vem de `articles/services/aws.py` (`resource('dynamodb')`): região em `AWS_REGION`, timeouts de 3 s e 10 s, 3 tentativas.

A tabela é criada à mão no console da AWS (ver [docs/aws/04-dynamodb.md](../aws/04-dynamodb.md)). O compose não a cria.

## Credenciais dentro do container

O `boto3` procura credenciais, nesta ordem de interesse para nós:

| Origem | Funciona no container? | Observação |
|---|---|---|
| Variáveis `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (e `AWS_SESSION_TOKEN` em contas temporárias, como o Learner Lab) | Sim, se estiverem no `.env` (o `env_file` as injeta no `backend`) | O `.env.example` atual **não lista essas variáveis**; é preciso acrescentá-las. Credenciais temporárias expiram com a sessão |
| `~/.aws/credentials` | Só se a pasta for montada como volume | O compose não monta |
| IAM Role da EC2 (instance profile, via serviço de metadados) | Sim, mas só se o limite de saltos (*hop limit*) do IMDSv2 for pelo menos 2 | Com o padrão (1), o container, que está um salto atrás do host, não alcança as credenciais |

Atenção à contradição com o trabalho 1: [docs/aws/00-preparacao.md](../aws/00-preparacao.md) manda **não** pôr chaves AWS no `.env` da EC2 (a LabRole resolvia). Com Docker, ou se põem as chaves no `.env`, ou se ajusta o hop limit da instância.

## Como verificar se está gravando

Como o erro é engolido, o teste correto é olhar o resultado, não a resposta da API:

1. Criar um artigo pela tela.
2. `docker compose logs backend | grep "gravar o log"`: se aparecer, a gravação falhou.
3. Console da AWS, DynamoDB > Tabelas > `logs_crud` > Explorar itens: deve haver um item `CREATE` com o id do artigo.

## Armazenamento e consulta

A spec pontua "armazenamento **e consulta**" (1 pt). Hoje o código **só grava** (`put_item`); não existe rota da API que leia o log. A leitura acontece apenas nos testes de integração (`articles/tests/integration/test_dynamodb.py`, que confere chave, conteúdo e ordem cronológica) e pelo console da AWS. Ver [limitações](07-estudo-arguicao.md#limitações-conhecidas).

## Perguntas prováveis

1. **Por que o DynamoDB continua na AWS?** A spec exige (item 1a). Os outros serviços foram trocados por containers; este permanece como serviço gerenciado.
2. **Por que o log não fica no Postgres?** Só recebe escritas, cresce sem parar e não tem relações. Isola essa carga do banco principal.
3. **Qual a chave da tabela?** `article_id` (partição) + `timestamp` (ordenação): dá o histórico de um artigo em ordem.
4. **E se o DynamoDB estiver inacessível?** O CRUD continua; só o log daquela ação se perde, com um erro no log do backend.
5. **Como o container autentica na AWS?** Por variáveis de ambiente no `.env` ou pela role da instância (com hop limit 2). Nunca no código nem na imagem.
6. **Por que `Decimal` e não `float`?** O DynamoDB rejeita `float`. O `serialize()` do artigo só tem textos e inteiros, então o problema não aparece.

[← 4. Frontend e Nginx](04-frontend-nginx.md) | [Índice](README.md) | [6. CI e deploy →](06-ci-deploy.md)
