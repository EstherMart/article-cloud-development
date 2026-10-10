"""Rotas da API de artigos. As views só orquestram: a lógica de cada serviço AWS
fica em `services/` (ver services/README.md)."""
import json
import logging

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from accounts.tokens import token_required
from article_cloud.http import error, read_json

from .models import Article, Author, Tag
from services.dynamo_log import log_action
from services.s3 import upload_pdf, delete_pdf, presigned_url

logger = logging.getLogger(__name__)

TITULO_DUPLICADO = 'Já existe um artigo com esse título'
SEM_PERMISSAO = 'Você só pode alterar os seus próprios artigos'


def articles_queryset():
    """Artigos com usuário, autores e tags carregados em poucas consultas (evita N+1)."""
    return Article.objects.select_related('user').prefetch_related('authors', 'tags')


def serialize(article):
    return {
        'id': article.id,
        'title': article.title,
        'authors': [author.name for author in article.authors.all()],
        'area': article.area,
        'abstract': article.abstract,
        'translated_abstract': article.translated_abstract,
        'processing_status': article.processing_status,
        'upload_datetime': article.upload_datetime.isoformat(),
        'user': article.user.username,
        'tags': [tag.name for tag in article.tags.all()],
    }


def error(message, status):
    return JsonResponse({'erro': message}, status=status)

def fail(message, status, local):
    logger.error(f"Erro em {local} (STATUS {status}): {message}")
    return error(message, status)

def read_json(request):
    """Corpo da requisição como dict. Levanta ValueError se não for um objeto JSON."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError as exc:
        raise ValueError('JSON inválido') from exc
    if not isinstance(body, dict):
        raise ValueError('JSON inválido')
    return body


def clean_names(value):
    """Lista de nomes sem espaços sobrando e sem repetição, ou None se o formato for inválido."""
    if not isinstance(value, list) or not all(isinstance(name, str) for name in value):
        return None
    names = [name.strip() for name in value if name.strip()]
    return list(dict.fromkeys(names))


def set_authors(article, names):
    authors = [Author.objects.filter(name=name).first() or Author.objects.create(name=name) for name in names]
    article.authors.set(authors)


def set_tags(article, names):
    article.tags.set([Tag.objects.get_or_create(name=name)[0] for name in names])


def fetch_article(article_id):
    return articles_queryset().filter(id=article_id).first()

@method_decorator(csrf_exempt, name='dispatch')
class ArticleView(View):

    def get(self, request):
        articles = [serialize(a) for a in articles_queryset()]
        log_action('READ', 'list', {'count': len(articles)})
        return JsonResponse(articles, safe=False)

    @token_required
    def post(self, request):

        title = request.POST.get('title')
        area = request.POST.get('area')
        abstract = request.POST.get('abstract', '')
        pdf_file = request.FILES.get('file')

        try:
            authors = json.loads(request.POST.get('authors', '[]'))
            tags = json.loads(request.POST.get('tags', '[]'))
        except json.JSONDecodeError:
            return fail('Authors e tags devem estar no formato JSON válido!', 400, 'ArticleView.post')

        authors = clean_names(authors)
        tags = clean_names(tags)

        if not title or not area or not authors:
            return fail('title, authors e area são obrigatórios', 400, 'ArticleView.post')
        if tags is None or not isinstance(abstract, str):
            return fail('tags deve ser uma lista de textos e abstract deve ser texto', 400, 'ArticleView.post')
        if not pdf_file:
            return fail('O envio do PDF é obrigatório!', 400, 'ArticleView.post')

        try:
            with transaction.atomic():
                article = Article.objects.create(title=title, area=area, user=request.user, abstract=abstract)
                set_authors(article, authors)
                set_tags(article, tags)
                article.s3_key = upload_pdf(article.id, pdf_file)
                article.save()
        except IntegrityError:
            return fail(TITULO_DUPLICADO, 409, 'ArticleView.post')
        except Exception as e:
            return fail(f"Erro {str(e)} identificado!", 500, 'ArticleView.post')

        created_article = serialize(fetch_article(article.id))
        log_action('CREATE', str(article.id), created_article)

        return JsonResponse(
            {'mensagem': 'Artigo cadastrado com sucesso', 'article': serialize(fetch_article(article.id))},
            status=201,
        )


@method_decorator(csrf_exempt, name='dispatch')
class ArticleDetailsView(View):

    def get(self, request, id):
        article = fetch_article(id)
        if article is None:
            return fail('Artigo de id inexistente', 404, 'ArticleDetailsView.get')

        data = serialize(article)
        log_action('READ', str(id), data)
        return JsonResponse(data)

    @token_required
    def put(self, request, id):
        article = fetch_article(id)
        if article is None:
            return fail('Artigo de id inexistente', 404, 'ArticleDetailsView.put')
        if article.user_id != request.user.id:
            return fail(SEM_PERMISSAO, 403, 'ArticleDetailsView.put')

        try:
            body = read_json(request)
        except ValueError as e:
            return fail(str(e), 400, 'ArticleDetailsView.put')

        title = body.get('title')
        area = body.get('area')
        authors = clean_names(body.get('authors', []))
        tags = clean_names(body['tags']) if 'tags' in body else None

        if not title or not area or not authors:
            return fail('title, authors e area são obrigatórios', 400, 'ArticleDetailsView.put')
        if 'tags' in body and tags is None:
            return fail('tags deve ser uma lista de textos', 400, 'ArticleDetailsView.put')

        try:
            with transaction.atomic():
                article.title = title
                article.area = area
                if isinstance(body.get('abstract'), str):
                    article.abstract = body['abstract']
                article.save()
                set_authors(article, authors)
                if tags is not None:
                    set_tags(article, tags)
        except IntegrityError:
            return fail(TITULO_DUPLICADO, 409, 'ArticleDetailsView.put')

        updated_article = serialize(fetch_article(id))
        log_action('UPDATE', str(id),  updated_article)

        return JsonResponse({'mensagem': 'Artigo atualizado com sucesso', 'article': serialize(fetch_article(id))})

    @token_required
    def delete(self, request, id):
        article = fetch_article(id)
        if article is None:
            return fail('Artigo de id inexistente', 404, 'ArticleDetailsView.delete')
        if article.user_id != request.user.id:
            return fail(SEM_PERMISSAO, 403, 'ArticleDetailsView.delete')
        if (article.s3_key):
            try:
                delete_pdf(article.s3_key)
            except Exception as e:
                return fail(f"Erro {str(e)} identificado!", 500, 'ArticleDetailsView.delete')
            
        # Falta: Invalidar o cache.

        deleted_data = serialize(article)
        article.delete()
        log_action('DELETE', str(id), deleted_data)

        return JsonResponse({'mensagem': 'Artigo deletado com sucesso'})


class ArticleSearchView(View):

    def get(self, request):
        query = request.GET.get('q', '')
        articles = articles_queryset().filter(
            Q(title__icontains=query)
            | Q(authors__name__icontains=query)
            | Q(area__icontains=query)
            | Q(tags__name__icontains=query)
        ).distinct()

        search_results = [serialize(a) for a in articles]
        log_action('READ', 'Search', {'query': query, 'count': len(search_results)})
        return JsonResponse(search_results, safe=False)


class ArticleDownloadView(View):

    def get(self, request, id):
        article = fetch_article(id)
        if ((article is None) or (not article.s3_key)):
            return fail("Arquivo inexistente!", 404, 'ArticleDownloadView.get')

        try:
            url = presigned_url(article.s3_key)

            log_action('READ', str(id), {'s3_key': article.s3_key})

            return JsonResponse({
                'mensagem': 'Download do artigo já disponível!',
                'download URL': url
            })

        except Exception as e:
            return fail(f"Erro {str(e)} identificado!", 500, 'ArticleDownloadView.get')
        
