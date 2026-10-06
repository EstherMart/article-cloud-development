from django.db import models
from django.contrib.auth.models import User


#podemos criar uma tabela com áreas e relacionar artigos -> area
#classe caso coloquemos múltiplos autores 
class Author(models.Model):
    name = models.CharField(max_length=255)
    
class Tag(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True
    )
    
#implementação da tabela artigo seguindo o modelo elaborado pela Esther
class Article(models.Model):


    #é necessário status de processamento?
    class ProcessingStatus(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        PROCESSADO = 'PROCESSADO', 'Processado'
        PROCESSANDO = 'PROCESSANDO', 'Processando'
        ERRO = 'ERRO', 'Erro'

    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDENTE
    )

    #authors = models.ManyToManyField(Author) múltiplos autores?
    author = models.CharField(max_length=255)

    title = models.CharField(
        max_length=255,
        unique=True
        #unique = true?
    )

    upload_datetime = models.DateTimeField(
        auto_now_add=True
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    area = models.CharField(max_length=255)

    # resumo digitado no cadastro; o worker grava a tradução em translated_abstract
    abstract = models.TextField(blank=True)
    translated_abstract = models.TextField(blank=True)
    # chave do PDF no S3 (preenchida depois de salvar o registro, usa o id)
    s3_key = models.CharField(max_length=512, blank=True)

    tags = models.ManyToManyField(Tag, blank=True)
    def __str__(self):
        return self.title