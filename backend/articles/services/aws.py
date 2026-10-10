"""Fábrica de clientes boto3, usada por todos os módulos desta pasta.

Não há chaves de acesso no código. Na EC2, o boto3 usa a IAM Role (LabRole)
automaticamente. Localmente, use `aws configure` ou as variáveis
AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN (Learner Lab).

Boas práticas aplicadas aqui:
- O cliente é criado uma vez por serviço e região (criar um cliente a cada chamada
  custa tempo e refaz a busca de credenciais).
- Clientes boto3 são thread-safe. Resources não são, por isso cada thread tem os seus.
- Timeouts e retries explícitos: sem eles, um serviço lento trava a requisição da API.
- S3 assina com Signature v4 (exigida pelas URLs pré-assinadas de buckets privados).
"""
import os
import threading
from functools import lru_cache

DEFAULT_REGION = 'us-east-1'
_local = threading.local()


def _region():
    return os.environ.get('AWS_REGION', DEFAULT_REGION)


def _config(service_name):
    # Import dentro da função: o projeto continua importável sem boto3 instalado.
    from botocore.config import Config

    options = {
        'retries': {'max_attempts': 3, 'mode': 'standard'},
        'connect_timeout': 3,
        'read_timeout': 10,
    }
    if service_name == 's3':
        options['signature_version'] = 's3v4'
    return Config(**options)


@lru_cache(maxsize=None)
def _client(service_name, region):
    import boto3

    return boto3.client(service_name, region_name=region, config=_config(service_name))


def client(service_name):
    """Cliente compartilhado (thread-safe) do serviço na região de AWS_REGION."""
    return _client(service_name, _region())


def resource(service_name):
    """Resource do serviço. Um por thread e região, porque resources não são thread-safe."""
    import boto3

    resources = _local.__dict__.setdefault('resources', {})
    key = (service_name, _region())
    if key not in resources:
        resources[key] = boto3.resource(service_name, region_name=_region(), config=_config(service_name))
    return resources[key]
