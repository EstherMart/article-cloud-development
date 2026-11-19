"""PDFs no minIO: bucket privado em MINIO_BUCKET, chave `artigos/{id}.pdf`, download por URL pré-assinada.
"""

from .aws import minio_client
from django.conf import settings
from botocore.exceptions import ClientError
import os

KEY_TEMPLATE = 'artigos/{article_id}.pdf'
BUCKET_READY = False 

# Construindo a estrutura do minIO para funcionar como um s3

# Criacao do bucket, caso seja necessario
def create_bucket():

    global BUCKET_READY

    # Se o bucket ja esta criado, simplesmente acabamos com a funcao sem gerar nada
    if (BUCKET_READY == True):
        return

    # Caso contrario, criamos o bucket
    try:
        minio_client().create_bucket(Bucket = settings.MINIO_BUCKET)
    except ClientError as e:
        if e.response['Error']['Code'] != 'BucketAlreadyOwnedByYou':
            raise

    # Modificando o valor de bucket ready
    BUCKET_READY = True


def upload_pdf(article_id, file_obj):

    # Criando bucket se necessario
    create_bucket()

    s3_key = KEY_TEMPLATE.format(article_id=article_id)
    minio_client().upload_fileobj(
        file_obj,
        settings.MINIO_BUCKET,
        s3_key,
        ExtraArgs={'ContentType': 'application/pdf'}
    )
    return s3_key


def presigned_url(s3_key, expires_in=300):
    url = minio_client(public=True).generate_presigned_url(
        'get_object',
        Params={
            'Bucket': settings.MINIO_BUCKET,
            'Key': s3_key
        },
        ExpiresIn=expires_in
    )
    
    internal_url = os.getenv('MINIO_ENDPOINT_URL', 'http://minio:9000')
    public_url = os.getenv('MINIO_PUBLIC_ENDPOINT_URL', internal_url)
    
    return url.replace(internal_url, public_url)


def delete_pdf(s3_key):
    minio_client().delete_object(
        Bucket=settings.MINIO_BUCKET,
        Key=s3_key
    )
