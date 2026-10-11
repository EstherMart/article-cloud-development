"""Fábrica de clientes boto3: um por serviço e região, com timeouts e retries. Sem chaves no código:
na EC2 vale a IAM Role; localmente, `aws configure` ou as variáveis AWS_*.
"""
import os
import threading
from functools import lru_cache

DEFAULT_REGION = 'us-east-1'
_local = threading.local()


def _region():
    return os.environ.get('AWS_REGION', DEFAULT_REGION)


def _config(service_name):
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
