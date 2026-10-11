"""Log das ações de escrita no DynamoDB (tabela em DYNAMODB_TABLE).

Chave: `article_id` (String) e `timestamp` (String, ISO 8601). Falha de log é registrada e não derruba o CRUD.
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
