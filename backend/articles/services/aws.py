"""Fábrica de clientes boto3, usada por todos os módulos desta pasta.

Não há chaves de acesso no código. Na EC2, o boto3 usa a IAM Role (LabRole)
automaticamente. Localmente, use `aws configure` ou as variáveis
AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN (Learner Lab).
"""
import os


def client(service_name):
    # Import dentro da função: o projeto continua importável sem boto3 instalado.
    import boto3

    return boto3.client(service_name, region_name=os.environ.get('AWS_REGION', 'us-east-1'))


def resource(service_name):
    import boto3

    return boto3.resource(service_name, region_name=os.environ.get('AWS_REGION', 'us-east-1'))
