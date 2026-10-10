"""Helpers HTTP compartilhados pelas views de todos os apps."""
import json

from django.http import JsonResponse


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
