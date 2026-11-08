from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import servicos


class LoginSerializer(serializers.Serializer):
    usuario = serializers.CharField()
    senha = serializers.CharField(write_only=True, trim_whitespace=False)


def _resposta_da_sessao(membro) -> dict:
    return {
        "usuario": membro.usuario.username,
        "dono": {"id": str(membro.dono.id), "nome": membro.dono.nome},
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SessaoView(APIView):
    """Login (POST), sessão atual (GET) e logout (DELETE). Entrega o cookie `csrftoken`."""

    def get_permissions(self):
        return [AllowAny() if self.request.method == "POST" else IsAuthenticated()]

    @extend_schema(request=LoginSerializer, responses={200: None, 400: None})
    def post(self, request):
        # O DRF só confere o CSRF de quem já está logado; no login conferimos aqui.
        SessionAuthentication().enforce_csrf(request)
        dados = LoginSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        membro = servicos.autenticar(
            request, dados.validated_data["usuario"], dados.validated_data["senha"]
        )
        if membro is None:
            return Response(
                {"detail": "Usuário ou senha incorretos."}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(_resposta_da_sessao(membro))

    @extend_schema(responses={200: None})
    def get(self, request):
        return Response(
            {
                "usuario": request.user.username,
                "dono": {"id": str(request.dono.id), "nome": request.dono.nome},
            }
        )

    @extend_schema(responses={204: None})
    def delete(self, request):
        servicos.encerrar(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
