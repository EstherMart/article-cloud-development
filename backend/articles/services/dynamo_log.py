"""Log das ações de CRUD no DynamoDB.

A spec exige em toda ação: o tipo da ação, os dados manipulados e a hora.
Tabela: logs_crud (nome em DYNAMODB_TABLE).

Decisão em aberto: chave da tabela. Sugestão: partição `article_id` (string)
e ordenação `timestamp` (ISO 8601). Para o DELETE, o log continua existindo
mesmo depois de o artigo sumir do RDS.

Atributos sugeridos: action (CREATE/READ/UPDATE/DELETE), data (dados do artigo
em dict simples), timestamp, article_id.
"""
from .aws import resource

ACTIONS = ('CREATE', 'READ', 'UPDATE', 'DELETE')


def log_action(action, article_id, data):
    """Grava um item em logs_crud.

    Como fazer: resource('dynamodb').Table(nome).put_item(Item={...}).
    Cuidado: o DynamoDB não aceita float, use int ou str (ou Decimal).
    Falha de log não deve derrubar o CRUD: capture a exceção, registre com
    logging e siga, ou decida em grupo que o log é obrigatório.
    """
    raise NotImplementedError
