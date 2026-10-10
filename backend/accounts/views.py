"""Cadastro e login. O login devolve um token para o header Authorization (ver tokens.py)."""
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from article_cloud.http import error, read_json

from .tokens import make_token


def validate_new_user(username, email, password):
    """Mensagem do primeiro problema encontrado, ou None se os dados forem válidos."""
    if not all(isinstance(value, str) and value.strip() for value in (username, email, password)):
        return 'username, email e password são obrigatórios'
    try:
        UnicodeUsernameValidator()(username)
        validate_email(email)
        validate_password(password, User(username=username, email=email))
    except ValidationError as exc:
        return exc.messages[0]
    return None


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(View):

    def post(self, request):
        try:
            body = read_json(request)
        except ValueError as exc:
            return error(str(exc), 400)

        username, email, password = (body.get(key) for key in ('username', 'email', 'password'))
        problem = validate_new_user(username, email, password)
        if problem:
            return error(problem, 400)

        username = username.strip()
        if User.objects.filter(username__iexact=username).exists():
            return error('Esse nome de usuário já está em uso', 409)

        User.objects.create_user(username=username, email=email.strip(), password=password)
        return JsonResponse({'mensagem': 'Usuário cadastrado com sucesso'}, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(View):

    def post(self, request):
        try:
            body = read_json(request)
        except ValueError as exc:
            return error(str(exc), 400)

        username, password = body.get('username'), body.get('password')
        if not isinstance(username, str) or not isinstance(password, str):
            return error('username e password são obrigatórios', 400)

        user = authenticate(request, username=username.strip(), password=password)
        if user is None:
            return error('Usuário ou senha inválidos', 401)
        return JsonResponse({'token': make_token(user), 'username': user.username})
