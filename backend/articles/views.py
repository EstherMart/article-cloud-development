"""Rotas da API de artigos. As views só orquestram: a lógica de cada serviço AWS
fica em `services/` (ver services/README.md)."""
import json

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
import boto3
from django.conf import settings

from .models import Article, Author, Tag

TITULO_DUPLICADO = 'Já existe um artigo com esse título'


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
        return JsonResponse([serialize(a) for a in articles_queryset()], safe=False)

    def post(self, request):

        title = request.POST.get('title')
        area = request.POST.get('area')
        username = request.POST.get('user')
        abstract = request.POST.get('abstract', '')
        pdf_file = request.FILES.get('file')

        try:
            authors = json.loads(request.POST.get('authors', '[]'))
            tags = json.loads(request.POST.get('tags', '[]'))
        except json.JSONDecodeError:
            return error('Authors e tags devem estar no formato JSON válido!', 400)

        authors = clean_names(authors)
        tags = clean_names(tags)

        if not title or not area or not username or not authors:
            return error('title, authors, area e user são obrigatórios', 400)
        if tags is None or not isinstance(abstract, str):
            return error('tags deve ser uma lista de textos e abstract deve ser texto', 400)
        if not pdf_file:
            return error('O envio do PDF é obrigatório!', 400)

        user = User.objects.filter(username=username).first()
        if user is None:
            return error('Usuário não encontrado', 404)

        try:
            with transaction.atomic():
                article = Article.objects.create(title=title, area=area, user=user, abstract=abstract)
                set_authors(article, authors)
                set_tags(article, tags)

                s3_client = boto3.client(
                    's3',
                    aws_access_key_id = settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY,
                    aws_session_token = settings.AWS_SESSION_TOKEN,
                    region_name = settings.AWS_S3_REGION_NAME
                )
                s3_key = f"artigos/{article.id}-{pdf_file.name}"
                s3_client.upload_fileobj(
                    pdf_file,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    s3_key
                )
                article.s3_key = s3_key
                article.save()
        except IntegrityError:
            return error(TITULO_DUPLICADO, 409)
        except Exception as e:
            return error(f"Erro {str(e)} identificado!", 500)

        return JsonResponse(
            {'mensagem': 'Artigo cadastrado com sucesso', 'article': serialize(fetch_article(article.id))},
            status=201,
        )


@method_decorator(csrf_exempt, name='dispatch')
class ArticleDetailsView(View):

    def get(self, request, id):
        article = fetch_article(id)
        if article is None:
            return error('Artigo de id inexistente', 404)
        return JsonResponse(serialize(article))

    def put(self, request, id):
        article = fetch_article(id)
        if article is None:
            return error('Artigo de id inexistente', 404)

        try:
            body = read_json(request)
        except ValueError as exc:
            return error(str(exc), 400)

        title = body.get('title')
        area = body.get('area')
        authors = clean_names(body.get('authors', []))
        tags = clean_names(body['tags']) if 'tags' in body else None

        if not title or not area or not authors:
            return error('title, authors e area são obrigatórios', 400)
        if 'tags' in body and tags is None:
            return error('tags deve ser uma lista de textos', 400)

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
            return error(TITULO_DUPLICADO, 409)

        return JsonResponse({'mensagem': 'Artigo atualizado com sucesso', 'article': serialize(fetch_article(id))})

    def delete(self, request, id):
        article = fetch_article(id)
        if article is None:
            return error('Artigo de id inexistente', 404)
        if (article.s3_key):
            try:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id = settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY,
                    aws_session_token = settings.AWS_SESSION_TOKEN,
                    region_name = settings.AWS_S3_REGION_NAME
                )
                s3_client.delete_object(
                    Bucket = settings.AWS_STORAGE_BUCKET_NAME,
                    Key = article.s3_key
                )
            except Exception as e:
                return error(f"Erro {str(e)} identificado!", 500)
        # Falta: Registrar no DynamoDB e invalidar o cache.
        article.delete()
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
        return JsonResponse([serialize(a) for a in articles], safe=False)


class ArticleDownloadView(View):

    def get(self, request, id):
        article = fetch_article(id)
        if ((article is None) or (not article.s3_key)):
            return error("Arquivo inexistente!", 404)

        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id = settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY,
                aws_session_token = settings.AWS_SESSION_TOKEN,
                region_name = settings.AWS_S3_REGION_NAME
            )

            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params = {
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': article.s3_key
                },
                ExpiresIn = 3000
            )

            return JsonResponse({
                'mensagem': 'Download do artigo já disponível!',
                'download URL': presigned_url
            })

        except Exception as e:
            return error(f"Erro {str(e)} identificado!", 500)
        
