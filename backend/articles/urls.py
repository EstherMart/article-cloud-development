from django.urls import path
from . import views

#search antes para evitar que alguma search se confunda com id?
urlpatterns = [
    path('articles/', views.ArticleView.as_view(), name = 'articles'),
    path('articles/<int:id>/', views.ArticleDetailsView.as_view(), name = 'article_details'),
    path('articles/search/', views.ArticleSearchView.as_view(), name = 'articles_search'),
    path('articles/<int:id>/download/', views.ArticleDownloadView.as_view(), name = 'article_download'),
]