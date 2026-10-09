from django.contrib.auth.models import User
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Article(models.Model):

    class ProcessingStatus(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        PROCESSADO = 'PROCESSADO', 'Processado'
        PROCESSANDO = 'PROCESSANDO', 'Processando'
        ERRO = 'ERRO', 'Erro'

    # PENDENTE (cadastrado) -> PROCESSANDO (worker pegou) -> PROCESSADO ou ERRO
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDENTE,
    )
    title = models.CharField(max_length=255, unique=True)
    area = models.CharField(max_length=255)
    authors = models.ManyToManyField(Author, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    upload_datetime = models.DateTimeField(auto_now_add=True)

    # Resumo digitado no cadastro. O worker grava a tradução em translated_abstract.
    abstract = models.TextField(blank=True)
    translated_abstract = models.TextField(blank=True)
    # Chave do PDF no S3 (artigos/{id}.pdf). Preenchida depois de salvar o registro.
    s3_key = models.CharField(max_length=512, blank=True)

    def __str__(self):
        return self.title
