"""PDFs no S3: bucket privado em S3_BUCKET, chave `artigos/{id}.pdf`, download por URL pré-assinada.
"""
from django.conf import settings

from .aws import client

KEY_TEMPLATE = 'artigos/{article_id}.pdf'


def upload_pdf(article_id, file_obj):

    s3_key = KEY_TEMPLATE.format(article_id=article_id)
    client('s3').upload_fileobj(
        file_obj,
        settings.AWS_STORAGE_BUCKET_NAME,
        s3_key,
        ExtraArgs={'ContentType': 'application/pdf'}
    )
    return s3_key


def presigned_url(s3_key, expires_in=300):
    return client('s3').generate_presigned_url(
        'get_object',
        Params={
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': s3_key
        },
        ExpiresIn=expires_in
    )


def delete_pdf(s3_key):
    client('s3').delete_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=s3_key
    )
