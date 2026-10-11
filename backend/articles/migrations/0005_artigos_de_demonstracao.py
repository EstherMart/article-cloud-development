"""Artigos de demonstração para a arguição, dono `demo` (com senha só se DEMO_USER_PASSWORD existir).

Nascem sem PDF: rode `python manage.py carregar_demo_pdfs` depois. Não roda nos testes nem com
SEED_DEMO_DATA=0, não duplica por título e `migrate articles 0004` apaga só esses artigos.
"""
import os
from datetime import timedelta

from django.conf import settings
from django.db import migrations
from django.utils import timezone

from articles.demo.artigos import ARTIGOS, USUARIO_DEMO


def criar_artigos(apps, schema_editor):
    if not settings.SEED_DEMO_DATA:
        return
    User = apps.get_model('auth', 'User')
    Article = apps.get_model('articles', 'Article')
    Author = apps.get_model('articles', 'Author')
    Tag = apps.get_model('articles', 'Tag')

    usuario, criado = User.objects.get_or_create(username=USUARIO_DEMO)
    if criado:
        senha = os.environ.get('DEMO_USER_PASSWORD', '')
        if senha:
            from django.contrib.auth.hashers import make_password
            usuario.password = make_password(senha)
        else:
            usuario.password = '!'  # marca de senha inutilizável do Django: ninguém entra como `demo`
        usuario.save()

    agora = timezone.now()
    for posicao, dados in enumerate(ARTIGOS):
        if Article.objects.filter(title=dados['title']).exists():
            continue
        artigo = Article.objects.create(
            title=dados['title'],
            area=dados['area'],
            user=usuario,
            abstract=dados['abstract'],
            translated_abstract=dados['translated'],
            processing_status=dados['status'],
        )
        artigo.authors.set([Author.objects.get_or_create(name=nome)[0] for nome in dados['authors']])
        artigo.tags.set([Tag.objects.get_or_create(name=nome)[0] for nome in dados['tags']])
        # upload_datetime é automático; espalha as datas para "mais recentes" ter ordem.
        Article.objects.filter(pk=artigo.pk).update(upload_datetime=agora - timedelta(days=posicao, hours=posicao))


def apagar_artigos(apps, schema_editor):
    Article = apps.get_model('articles', 'Article')
    Article.objects.filter(title__in=[dados['title'] for dados in ARTIGOS], user__username=USUARIO_DEMO).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0004_article_abstract_article_s3_key_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(criar_artigos, apagar_artigos),
    ]
