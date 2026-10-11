from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include



def health(request):
    """Health check do ALB: responde 200 sem consultar banco, Redis ou AWS."""
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('health/', health, name='health'),
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('articles.urls')),
]
