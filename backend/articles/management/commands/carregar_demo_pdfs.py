"""Gera e envia ao S3 um PDF de várias páginas para cada artigo de demonstração.

Uso: `python manage.py carregar_demo_pdfs` (S3) ou `--saida pasta` (só grava em disco, sem AWS).
Rode depois do `migrate`; repetir é seguro. Não publica no SNS.
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from articles.demo.artigos import ARTIGOS, USUARIO_DEMO, secoes_demo
from articles.demo.pdf import documento
from articles.models import Article


class Command(BaseCommand):
    help = 'Gera e envia ao S3 os PDFs dos artigos de demonstração.'

    def add_arguments(self, parser):
        parser.add_argument('--saida', help='Pasta local onde gravar os PDFs, em vez de enviar ao S3.')

    def handle(self, *args, **opcoes):
        saida = Path(opcoes['saida']) if opcoes['saida'] else None
        if saida:
            saida.mkdir(parents=True, exist_ok=True)
        else:
            from articles.services.cache import invalidate_article
            from articles.services.s3 import upload_pdf

        enviados = 0
        for dados in ARTIGOS:
            artigo = Article.objects.filter(title=dados['title'], user__username=USUARIO_DEMO).first()
            if artigo is None:
                raise CommandError('Artigo de demonstração não encontrado. Rode `python manage.py migrate` antes.')
            pdf = documento(dados['title'], secoes_demo(dados))
            if saida:
                (saida / f'demo_{artigo.id:02d}.pdf').write_bytes(pdf)
            else:
                from io import BytesIO
                artigo.s3_key = upload_pdf(artigo.id, BytesIO(pdf))
                artigo.save(update_fields=['s3_key'])
                invalidate_article(artigo.id)
            enviados += 1
            self.stdout.write(f'  {artigo.id}: {dados["title"]}')
        destino = str(saida) if saida else 'o S3'
        self.stdout.write(self.style.SUCCESS(f'{enviados} PDFs gravados em {destino}.'))
