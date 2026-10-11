"""Log das ações de CRUD no DynamoDB.

A spec exige em toda ação: o tipo da ação, os dados manipulados e a hora.
Tabela: logs_crud (nome em DYNAMODB_TABLE).

Chave da tabela: partição `article_id` (string) e ordenação `timestamp`
(ISO 8601). Para o DELETE, o log continua existindo mesmo depois de o artigo
sumir do RDS.

Atributos: action (CREATE, UPDATE ou DELETE), data (dados do artigo em dict
simples), timestamp, article_id. Falha de log é registrada e não derruba o CRUD.
"""
import logging
from datetime import datetime, timezone

from django.conf import settings

from .aws import resource

logger = logging.getLogger(__name__)


def log_action(action, article_id, data):
    try:
        table = resource('dynamodb').Table(settings.AWS_DYNAMODB_TABLE_NAME)
        table.put_item(
            Item={
                'article_id': str(article_id),
                'data': data,
                'action': action,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
        )

    except Exception:
        logger.exception('Não foi possível gravar o log %s do artigo %s', action, article_id)
