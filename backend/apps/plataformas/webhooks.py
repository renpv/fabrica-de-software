"""Recebimento de webhooks do GitHub e do GitLab: rotas públicas, sem login nem CSRF.

A autenticação é a assinatura (GitHub) ou o token (GitLab), verificada em `servicos.py` antes de
qualquer gravação. Aqui só se lê o corpo cru e os cabeçalhos e se devolve um JSON curto.
"""

from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse
from django.http.request import RawPostDataException
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import servicos


def _resposta(r: servicos.RespostaWebhook) -> JsonResponse:
    return JsonResponse({"detail": r.detail}, status=r.status)


def _corpo(request) -> bytes | None:
    """O corpo cru, ou None se passar do limite do Django (DATA_UPLOAD_MAX_MEMORY_SIZE)."""
    try:
        return request.body
    except RequestDataTooBig, RawPostDataException:
        return None


@csrf_exempt
@require_POST
def github(request):
    corpo = _corpo(request)
    if corpo is None:
        return JsonResponse({"detail": "Corpo grande demais."}, status=413)
    h = request.headers
    return _resposta(
        servicos.receber_webhook_github(
            corpo,
            h.get("X-Hub-Signature-256", ""),
            h.get("X-GitHub-Event", ""),
            h.get("X-GitHub-Delivery", ""),
        )
    )


@csrf_exempt
@require_POST
def gitlab(request, conexao_id):
    corpo = _corpo(request)
    if corpo is None:
        return JsonResponse({"detail": "Corpo grande demais."}, status=413)
    h = request.headers
    return _resposta(
        servicos.receber_webhook_gitlab(
            conexao_id,
            corpo,
            h.get("X-Gitlab-Token", ""),
            h.get("X-Gitlab-Event", ""),
            h.get("X-Gitlab-Event-UUID", ""),
        )
    )
