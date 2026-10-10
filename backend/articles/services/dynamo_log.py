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
from django.conf import settings
from datetime import datetime, timezone
import logging
logger = logging.getLogger(__name__)

def log_action(action, article_id, data):

    try:
        dynamoDB = resource('dynamodb')

        table = dynamoDB.Table(settings.AWS_DYNAMODB_TABLE_NAME)
        table.put_item(
            Item = {
                'article_id': str(article_id),
                'data': data,
                'action': action,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Erro no log: {str(e)}")