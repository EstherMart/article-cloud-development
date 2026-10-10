"""Token de autenticação assinado com a SECRET_KEY, sem estado no servidor.

Sem tabela de sessões, qualquer instância do Auto Scaling valida o token, desde que
todas usem a mesma DJANGO_SECRET_KEY.
"""
from functools import wraps

from django.contrib.auth.models import User
from django.core import signing

from article_cloud.http import error

SALT = 'accounts.token'
MAX_AGE = 7 * 24 * 60 * 60  # segundos
HEADER_PREFIX = 'Token '


def make_token(user):
    return signing.dumps({'uid': user.pk}, salt=SALT)


def user_from_request(request):
    """Usuário do header `Authorization: Token <token>`, ou None se ausente ou inválido."""
    header = request.headers.get('Authorization', '')
    if not header.startswith(HEADER_PREFIX):
        return None
    try:
        payload = signing.loads(header[len(HEADER_PREFIX):], salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature:
        return None
    return User.objects.filter(pk=payload['uid']).first()


def token_required(method):
    """Decorator de método de view: responde 401 sem token válido e coloca o usuário em request.user."""

    @wraps(method)
    def wrapper(self, request, *args, **kwargs):
        user = user_from_request(request)
        if user is None:
            return error('Autenticação necessária', 401)
        request.user = user
        return method(self, request, *args, **kwargs)

    return wrapper
