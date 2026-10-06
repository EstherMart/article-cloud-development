from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from .models import Article

class ArticleView(View):

    def get(self, request):
        articles = Article.objects.all()

        data = [
            {
                "id": article.id,
                "title": article.title,
                "author": article.author,
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
        return JsonResponse({"mensagem": "Artigo cadastrado"})

class ArticleDetailsView(View):

    # GET methdod
    def get(self, request, id):
        return JsonResponse({"mensagem": f"Detalhes de {id}"})

    # PUT method
    def put(self, request, id):
        return JsonResponse({"mensagem": f"Artigo {id} atualizado com sucesso!"})

    # DELETE method
    def delete(self, request, id):
        return JsonResponse({"mensagem": f"Artigo {id} deletado com sucesso!"})

class ArticleSearchView(View):

    # GET method
    def get(self, request):
        return JsonResponse({"mensagem": "Resultados da busca:"})

class ArticleDownloadView(View):

    # GET method
    def get(self, request, id):
        return JsonResponse({"mensagem": "Arquivo baixado com sucesso!"})