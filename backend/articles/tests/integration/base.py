"""Base dos testes de integração (AWS real). Desligados por padrão.

Como ligar:
    RUN_AWS_INTEGRATION=1            liga os testes
    RUN_AWS_INTEGRATION_SLOW=1       liga também os lentos (ex.: teste da DLQ)

Cada classe de teste declara em REQUIRED_ENV as variáveis do .env de que precisa.
Se alguma estiver vazia, a classe inteira é pulada (o recurso ainda não existe).
O comando `python manage.py test` comum nunca chega à AWS.
"""
import os
import random
import unittest
from pathlib import Path

PDFS = Path(__file__).resolve().parents[1] / 'fixtures' / 'pdfs'


def slow(test):
    """Marca um teste lento. Só roda com RUN_AWS_INTEGRATION_SLOW=1."""
    return unittest.skipUnless(
        os.environ.get('RUN_AWS_INTEGRATION_SLOW') == '1',
        'teste lento: defina RUN_AWS_INTEGRATION_SLOW=1',
    )(test)


def novo_article_id():
    """Id que nunca colide com artigo real (o RDS começa em 1)."""
    return 900_000_000 + random.randint(0, 99_999_999)


class AwsIntegrationTestCase(unittest.TestCase):
    REQUIRED_ENV = ()

    @classmethod
    def setUpClass(cls):
        if os.environ.get('RUN_AWS_INTEGRATION') != '1':
            raise unittest.SkipTest('desligado: defina RUN_AWS_INTEGRATION=1 para usar a AWS real')
        missing = [name for name in cls.REQUIRED_ENV if not os.environ.get(name)]
        if missing:
            raise unittest.SkipTest(f'defina no .env: {", ".join(missing)}')
        super().setUpClass()
