from django.shortcuts import render
from django.views import View
from django.http import JsonResponse

class ArticleView(View):

    # GET method
    def get(self, request):
        return JsonResponse({"mensagem": "Lista de artigos"})

    # POST method
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