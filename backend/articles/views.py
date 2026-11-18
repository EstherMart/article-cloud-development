"""Rotas da API de artigos. As views só orquestram: a lógica de cada serviço AWS fica em `services/`."""
import json
import logging

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from botocore.exceptions import BotoCoreError, ClientError

from accounts.tokens import token_required
from article_cloud.http import error, read_json

from .models import Article, Author, Tag
from .services.dynamo_log import log_action
from .services.minIO import upload_pdf, delete_pdf, presigned_url
from .services.cache import get_or_set, invalidate_article
from .services.messaging import publish_article_created

logger = logging.getLogger(__name__)

# Mensagens devolvidas ao cliente que aparecem em mais de uma rota.
ARTIGO_INEXISTENTE = 'Artigo de id inexistente'
CAMPOS_OBRIGATORIOS = 'title, authors e area são obrigatórios'
TITULO_DUPLICADO = 'Já existe um artigo com esse título'
SEM_PERMISSAO = 'Você só pode alterar os seus próprios artigos'
ERRO_ARMAZENAMENTO = 'Falha ao acessar o armazenamento de arquivos'
ERRO_PROCESSAMENTO = 'O artigo foi salvo, mas não foi possível iniciar o processamento.'

MAX_PDF_MB = 10
MAX_PDF_BYTES = MAX_PDF_MB * 1024 * 1024


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


def fail(request, message, status, **extra):
    """Registra o erro (método, rota e status) e devolve a resposta JSON de erro."""
    logger.error('%s %s -> %s: %s', request.method, request.path, status, message)
    return error(message, status, **extra)


def discard_pdf(s3_key):
    """Apaga o PDF do S3. Falha só é registrada: o pior caso é um objeto órfão."""
    try:
        delete_pdf(s3_key)
    except (ClientError, BotoCoreError):
        logger.exception('Não foi possível apagar %s do S3', s3_key)


def start_processing(article):
    """Publica o evento no RabbitMQ. Se falhar, marca o artigo como ERRO e devolve False."""
    try:
        publish_article_created(article.id, article.s3_key, settings.MINIO_BUCKET)
    except RuntimeError:  # inclui MessagingError (broker fora do ar) e configuração ausente
        logger.exception('Não foi possível publicar o artigo %s no RabbitMQ.', article.id)
        status = Article.ProcessingStatus.ERRO
        ok = False
    else:
        status = Article.ProcessingStatus.PENDENTE
        ok = True
    try:
        Article.objects.filter(id=article.id).update(processing_status=status)
    except DatabaseError:
        logger.exception('Não foi possível gravar o status do artigo %s.', article.id)
    invalidate_article(article.id)
    return ok


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
        def db_loader():
            return [serialize(a) for a in articles_queryset()]
        articles = get_or_set('artigos:recentes', db_loader)
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
            return fail(request, 'Authors e tags devem estar no formato JSON válido!', 400)

        authors = clean_names(authors)
        tags = clean_names(tags)

        if not title or not area or not authors:
            return fail(request, CAMPOS_OBRIGATORIOS, 400)
        if tags is None or not isinstance(abstract, str):
            return fail(request, 'tags deve ser uma lista de textos e abstract deve ser texto', 400)
        if not pdf_file:
            return fail(request, 'O envio do PDF é obrigatório!', 400)
        if pdf_file.content_type != 'application/pdf':
            return fail(request, 'O arquivo deve ser um PDF', 415)
        if pdf_file.size > MAX_PDF_BYTES:
            return fail(request, f'O PDF deve ter no máximo {MAX_PDF_MB} MB', 413)

        uploaded_key = None
        try:
            with transaction.atomic():
                article = Article.objects.create(title=title, area=area, user=request.user, abstract=abstract)
                set_authors(article, authors)
                set_tags(article, tags)
                uploaded_key = upload_pdf(article.id, pdf_file)
                article.s3_key = uploaded_key
                article.save()
        except IntegrityError:
            return fail(request, TITULO_DUPLICADO, 409)
        except (ClientError, BotoCoreError):
            logger.exception('Falha ao enviar o PDF ao S3')
            return fail(request, ERRO_ARMAZENAMENTO, 502)
        except DatabaseError:
            if uploaded_key:
                discard_pdf(uploaded_key)
            raise

        created_article = serialize(fetch_article(article.id))
        invalidate_article(article.id)
        log_action('CREATE', str(article.id), created_article)

        if not start_processing(article):
            return fail(request, ERRO_PROCESSAMENTO, 503, article_id=article.id)

        return JsonResponse(
            {'mensagem': 'Artigo cadastrado com sucesso', 'article': serialize(fetch_article(article.id))},
            status=201,
        )


@method_decorator(csrf_exempt, name='dispatch')
class ArticleDetailsView(View):

    def get(self, request, id):
        def db_loader():
            article = fetch_article(id)
            return serialize(article) if article else None

        article_data = get_or_set(f'artigo:{id}', db_loader)
        if article_data is None:
            return fail(request, ARTIGO_INEXISTENTE, 404)

        return JsonResponse(article_data)

    @token_required
    def put(self, request, id):
        article = fetch_article(id)
        if article is None:
            return fail(request, ARTIGO_INEXISTENTE, 404)
        if article.user_id != request.user.id:
            return fail(request, SEM_PERMISSAO, 403)

        try:
            body = read_json(request)
        except ValueError as e:
            return fail(request, str(e), 400)

        title = body.get('title')
        area = body.get('area')
        authors = clean_names(body.get('authors', []))
        tags = clean_names(body['tags']) if 'tags' in body else None

        if not title or not area or not authors:
            return fail(request, CAMPOS_OBRIGATORIOS, 400)
        if 'tags' in body and tags is None:
            return fail(request, 'tags deve ser uma lista de textos', 400)

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
            return fail(request, TITULO_DUPLICADO, 409)

        updated_article = serialize(fetch_article(id))
        invalidate_article(id)
        log_action('UPDATE', str(id), updated_article)

        return JsonResponse({'mensagem': 'Artigo atualizado com sucesso', 'article': serialize(fetch_article(id))})

    @token_required
    def delete(self, request, id):
        article = fetch_article(id)
        if article is None:
            return fail(request, ARTIGO_INEXISTENTE, 404)
        if article.user_id != request.user.id:
            return fail(request, SEM_PERMISSAO, 403)

        deleted_data = serialize(article)
        s3_key = article.s3_key
        article.delete()
        if s3_key:
            discard_pdf(s3_key)
        invalidate_article(id)
        log_action('DELETE', str(id), deleted_data)

        return JsonResponse({'mensagem': 'Artigo deletado com sucesso'})


@method_decorator(csrf_exempt, name='dispatch')
class ArticleReprocessView(View):
    """Reenvia ao worker um artigo cujo processamento não foi iniciado ou falhou."""

    @token_required
    def post(self, request, id):
        article = fetch_article(id)
        if article is None:
            return fail(request, ARTIGO_INEXISTENTE, 404)
        if article.user_id != request.user.id:
            return fail(request, SEM_PERMISSAO, 403)
        if article.processing_status != Article.ProcessingStatus.ERRO:
            return fail(request, 'Só é possível reprocessar artigos com status ERRO', 409)
        if not start_processing(article):
            return fail(request, ERRO_PROCESSAMENTO, 503)
        return JsonResponse({'mensagem': 'Processamento reenviado', 'article': serialize(fetch_article(id))})


class ArticleSearchView(View):

    def get(self, request):
        query = request.GET.get('q', '')

        def db_loader():
            articles = articles_queryset().filter(
                Q(title__icontains=query)
                | Q(authors__name__icontains=query)
                | Q(area__icontains=query)
                | Q(tags__name__icontains=query)
            ).distinct()
            return [serialize(a) for a in articles]

        search_results = get_or_set(f'busca:{query}', db_loader)
        return JsonResponse(search_results, safe=False)


class ArticleDownloadView(View):

    def get(self, request, id):
        article = fetch_article(id)
        if article is None or not article.s3_key:
            return fail(request, 'Arquivo inexistente', 404)

        try:
            url = presigned_url(article.s3_key)

            return JsonResponse({
                'mensagem': 'Download do artigo já disponível!',
                'download_url': url
            })

        except (ClientError, BotoCoreError):
            logger.exception('Falha ao gerar a URL de download')
            return fail(request, ERRO_ARMAZENAMENTO, 502)
