"""Regras comuns dos testes de integração: ficam desligados por padrão.

Ligue com RUN_AWS_INTEGRATION=1. Cada arquivo de teste deve herdar de
AwsIntegrationTestCase e usar require_env() para pular o teste quando a
variável do serviço estiver vazia (o recurso ainda não foi criado).

Esqueleto (descomente quando for o primeiro teste de integração):

import os
import unittest


def require_env(*names):
    \"\"\"Pula o teste se alguma variável do .env estiver vazia.\"\"\"
    missing = [n for n in names if not os.environ.get(n)]
    return unittest.skipIf(bool(missing), f'defina no .env: {", ".join(missing)}')


class AwsIntegrationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('RUN_AWS_INTEGRATION') != '1':
            raise unittest.SkipTest('defina RUN_AWS_INTEGRATION=1 para rodar contra a AWS')
"""
