from django.urls import path

from . import views

# `articles/search/` vem antes de `articles/<int:id>/` para a busca não ser confundida com um id.
urlpatterns = [
    path('articles/', views.ArticleView.as_view(), name='articles'),
    path('articles/search/', views.ArticleSearchView.as_view(), name='articles_search'),
    path('articles/<int:id>/', views.ArticleDetailsView.as_view(), name='article_details'),
    path('articles/<int:id>/download/', views.ArticleDownloadView.as_view(), name='article_download'),
]
