from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import servicos
from .permissoes import TemDono
from .throttles import LoginPorUsuarioThrottle

MENSAGEM_CSRF = "Sessão expirada ou formulário inválido. Recarregue a página e tente de novo."


class SessaoAutenticacao(SessionAuthentication):
    """Autenticação por sessão com a recusa de CSRF em português."""

    def enforce_csrf(self, request):
        try:
            super().enforce_csrf(request)
        except exceptions.PermissionDenied as erro:
            raise exceptions.PermissionDenied(MENSAGEM_CSRF) from erro


class LoginSerializer(serializers.Serializer):
    usuario = serializers.CharField()
    senha = serializers.CharField(write_only=True, trim_whitespace=False)


def _resposta_da_sessao(usuario, dono) -> dict:
    return {
        "usuario": usuario.username,
        "dono": {"id": str(dono.id), "nome": dono.nome},
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SessaoView(APIView):
    """Login (POST), sessão atual (GET) e logout (DELETE). Entrega o cookie `csrftoken`."""

    authentication_classes = [SessaoAutenticacao]
    throttle_scope = "sessao"

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        if self.request.method == "GET":
            return [IsAuthenticated(), TemDono()]
        return [IsAuthenticated()]

    def get_throttles(self):
        # Só as tentativas de login são limitadas.
        return (
            [ScopedRateThrottle(), LoginPorUsuarioThrottle()]
            if self.request.method == "POST"
            else []
        )

    def throttled(self, request, wait):
        raise exceptions.Throttled(
            wait, detail="Muitas tentativas de login. Espere um minuto e tente de novo."
        )

    @extend_schema(request=LoginSerializer, responses={200: None, 400: None})
    def post(self, request):
        # O DRF só confere o CSRF de quem já está logado; no login conferimos aqui.
        SessaoAutenticacao().enforce_csrf(request)
        dados = LoginSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        membro = servicos.autenticar(
            request, dados.validated_data["usuario"], dados.validated_data["senha"]
        )
        if membro is None:
            return Response(
                {"detail": "Usuário ou senha incorretos."}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(_resposta_da_sessao(membro.usuario, membro.dono))

    @extend_schema(responses={200: None})
    def get(self, request):
        return Response(_resposta_da_sessao(request.user, request.dono))

    @extend_schema(responses={204: None})
    def delete(self, request):
        servicos.encerrar(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
