"""PDFs no S3. Branch: feat/s3-upload.

Regras:
- Bucket privado (nome em S3_BUCKET). Ninguém acessa o PDF direto.
- Chave: artigos/{id}.pdf. O id vem do RDS, por isso o registro é gravado antes.
- Download pelo cliente é por URL pré-assinada, nunca passando pela API nem pelo Redis.
"""
from .aws import client

KEY_TEMPLATE = 'artigos/{article_id}.pdf'


def upload_pdf(article_id, file_obj):
    """Envia o PDF e devolve a chave (s3_key).

    Como fazer: client('s3').upload_fileobj(file_obj, bucket, key,
    ExtraArgs={'ContentType': 'application/pdf'}).
    Se falhar, deixe a exceção subir: a view apaga o registro do RDS ou marca ERRO.
    """
    raise NotImplementedError


def presigned_url(s3_key, expires_in=300):
    """URL temporária de download.

    Como fazer: client('s3').generate_presigned_url('get_object',
    Params={'Bucket': bucket, 'Key': s3_key}, ExpiresIn=expires_in).
    """
    raise NotImplementedError


def delete_pdf(s3_key):
    """Remove o PDF (usado no DELETE do artigo).

    Como fazer: client('s3').delete_object(Bucket=bucket, Key=s3_key).
    """
    raise NotImplementedError
