from django.views import View
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Q
from .models import Article, Tag, Author
import json

#listar todos
@method_decorator(csrf_exempt, name='dispatch')
class ArticleView(View):

    def get(self, request):
        articles = Article.objects.all()

        data = [
            {
                "id": article.id,
                "title": article.title,
                "authors": [author.name for author in article.authors.all()],
                "processing_status": article.processing_status,
                "upload_datetime": article.upload_datetime.isoformat(),
                "user": article.user.username,
                "area": article.area,
                "tags": [tag.name for tag in article.tags.all()],
            }
            for article in articles
        ]

        return JsonResponse(data, safe=False)

    def post(self, request):
        try:
            body = json.loads(request.body)

            title = body.get("title")
            authors = body.get("authors", [])
            area = body.get("area")
            username = body.get("user")
            tags = body.get("tags", [])

            if not title or not authors or not area or not username:
                return JsonResponse(
                    {
                        "erro": "title, authors, area e user são obrigatórios"
                    },
                    status=400
                )

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse(
                    {"erro": "Usuário não encontrado"},
                    status=404
                )

            article = Article.objects.create(
                title=title,
                area=area,
                user=user
            )

            for author_name in authors:
                author, created = Author.objects.get_or_create(
                    name=author_name
                )
                article.authors.add(author)

            for tag_name in tags:
                tag, created = Tag.objects.get_or_create(
                    name=tag_name
                )
                article.tags.add(tag)

            return JsonResponse(
                {
                    "mensagem": "Artigo cadastrado com sucesso",
                    "article": {
                        "id": article.id,
                        "title": article.title,
                        "authors": [author.name for author in article.authors.all()],
                        "area": article.area,
                        "processing_status": article.processing_status,
                        "user": article.user.username,
                        "tags": [
                            tag.name
                            for tag in article.tags.all()
                        ],
                    }
                },
                status=201
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {"erro": "JSON inválido"},
                status=400
            )


#devolver um artigo
@method_decorator(csrf_exempt, name='dispatch')
class ArticleDetailsView(View):

    def get(self, request, id):
        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist:
            return JsonResponse({"erro": "Artigo de id inexistente"},status=404)
        data = {
            "id": article.id,
            "title": article.title,
            "authors": [author.name for author in article.authors.all()],
            "processing_status": article.processing_status,
            "upload_datetime": article.upload_datetime.isoformat(),
            "user": article.user.username,
            "area": article.area,
            "tags": [tag.name for tag in article.tags.all()],
        }
        return JsonResponse(data)

    def put(self, request, id):
        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist:
            return JsonResponse(
                {"erro": "Artigo de id inexistente"},
                status=404
            )

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"erro": "JSON inválido"},
                status=400
            )

        title = body.get("title")
        authors = body.get("authors", [])
        area = body.get("area")

        if not title or not authors or not area:
            return JsonResponse(
                {"erro": "title, authors e area são obrigatórios"},
                status=400
            )

        article.title = title
        article.authors.clear() 
        for author_name in authors:
            author, created = Author.objects.get_or_create(name=author_name)
            article.authors.add(author)
        article.area = area

        article.save()

        return JsonResponse({
            "mensagem": "Artigo atualizado com sucesso",
            "article": {
                "id": article.id,
                "title": article.title,
                "authors": [author.name for author in article.authors.all()],
                "processing_status": article.processing_status,
                "upload_datetime": article.upload_datetime.isoformat(),
                "user": article.user.username,
                "area": article.area,
                "tags": [tag.name for tag in article.tags.all()],
            }
        })

    def delete(self, request, id):
        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist:
            return JsonResponse(
                {"erro": "Artigo de id inexistente"},
                status=404
            )

        article.delete()

        return JsonResponse({
            "mensagem": "Artigo deletado com sucesso"
        })

class ArticleSearchView(View):

    def get(self, request):
        query = request.GET.get("q", "")
        #usando o Q para fazer operador lógico. negócio do django que faz busca pra gente 
        articles = Article.objects.filter(
            Q(title__icontains=query) |
            Q(authors__name__icontains=query) |
            Q(area__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct()

        data = [
            {
                "id": article.id,
                "title": article.title,
                "authors": [author.name for author in article.authors.all()],
                "processing_status": article.processing_status,
                "upload_datetime": article.upload_datetime.isoformat(),
                "user": article.user.username,
                "area": article.area,
                "tags": [tag.name for tag in article.tags.all()],
            }
            for article in articles
        ]

        return JsonResponse(data, safe=False)

class ArticleDownloadView(View):

    # GET method
    def get(self, request, id):
        return JsonResponse({"mensagem": "Arquivo baixado com sucesso!"})