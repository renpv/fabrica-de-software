from dataclasses import asdict

from django.http import HttpResponseRedirect
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.donos.mixins import EscopoDoDonoMixin
from apps.donos.permissoes import TemDono
from apps.donos.views import SessaoAutenticacao

from . import servicos
from .models import ConexaoPlataforma
from .serializers import (
    ConexaoPlataformaSerializer,
    ErroSerializer,
    InstaladoGitHubSerializer,
    ManifestoPedidoSerializer,
    ManifestoRespostaSerializer,
    RepositorioSerializer,
    RetornoGitHubSerializer,
    TesteDaConexaoSerializer,
)

_ERROS = {400: ErroSerializer, 502: ErroSerializer}


def _erro(erro: servicos.ErroDeFluxo | servicos.ErroDePlataforma) -> Response:
    return Response({"detail": str(erro)}, status=getattr(erro, "status", 502))


class _ViewDoDono(APIView):
    authentication_classes = [SessaoAutenticacao]
    permission_classes = [IsAuthenticated, TemDono]


class ManifestoGitHubView(_ViewDoDono):
    """Gera o manifesto do GitHub App e a URL de criação (o front envia por formulário)."""

    @extend_schema(
        request=ManifestoPedidoSerializer,
        responses={200: ManifestoRespostaSerializer, 400: ErroSerializer},
        operation_id="conexoes_plataforma_github_manifesto",
    )
    def post(self, request):
        pedido = ManifestoPedidoSerializer(data=request.data)
        pedido.is_valid(raise_exception=True)
        nome = pedido.validated_data["nome"].strip()
        if not nome:
            return Response({"nome": ["Informe um nome para a conexão."]}, status=400)
        return Response(servicos.gerar_manifesto(request.dono, nome))


def _validar_consulta(serializer_class, request):
    consulta = serializer_class(data=request.query_params)
    if not consulta.is_valid():
        return None
    return consulta.validated_data


class RetornoGitHubView(_ViewDoDono):
    """Volta do GitHub depois de criar o App: converte o código e leva para instalar."""

    @extend_schema(
        parameters=[
            OpenApiParameter("code", str, required=True),
            OpenApiParameter("state", str, required=True),
        ],
        responses={302: None, **_ERROS},
        operation_id="conexoes_plataforma_github_retorno",
    )
    def get(self, request):
        dados = _validar_consulta(RetornoGitHubSerializer, request)
        if dados is None:
            return Response({"detail": servicos.MENSAGEM_STATE}, status=400)
        try:
            destino = servicos.concluir_manifesto(request.dono, dados["code"], dados["state"])
        except servicos.ErroDeFluxo as erro:
            return _erro(erro)
        return HttpResponseRedirect(destino)


class InstaladoGitHubView(_ViewDoDono):
    """Volta do GitHub depois de instalar o App: grava a instalação e abre a tela no front."""

    @extend_schema(
        parameters=[
            OpenApiParameter("installation_id", str, required=True),
            OpenApiParameter("state", str, required=True),
        ],
        responses={302: None, **_ERROS},
        operation_id="conexoes_plataforma_github_instalado",
    )
    def get(self, request):
        dados = _validar_consulta(InstaladoGitHubSerializer, request)
        if dados is None:
            return Response({"detail": servicos.MENSAGEM_STATE}, status=400)
        try:
            destino = servicos.concluir_instalacao(
                request.dono, dados["installation_id"], dados["state"]
            )
        except servicos.ErroDeFluxo as erro:
            return _erro(erro)
        return HttpResponseRedirect(destino)


class ConexaoPlataformaViewSet(
    EscopoDoDonoMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Conexões do dono logado. Criam-se pelo fluxo de cada plataforma, não por POST aqui."""

    queryset = ConexaoPlataforma.objects.order_by("nome")
    serializer_class = ConexaoPlataformaSerializer
    authentication_classes = [SessaoAutenticacao]
    permission_classes = [IsAuthenticated, TemDono]

    def perform_destroy(self, instance):
        servicos.excluir_conexao(instance)

    @extend_schema(request=None, responses=TesteDaConexaoSerializer)
    @action(detail=True, methods=["post"], url_path="testar")
    def testar(self, request, pk=None):
        """Testa a conexão salva e grava o resultado nela."""
        r = servicos.testar_conexao(self.get_object())
        return Response({"ok": r.ok, "status": r.status, "mensagem": r.mensagem})

    @extend_schema(responses={200: RepositorioSerializer(many=True), 502: ErroSerializer})
    @action(detail=True, methods=["get"], url_path="repositorios", pagination_class=None)
    def repositorios(self, request, pk=None):
        """Todos os repositórios que a conexão enxerga."""
        try:
            repos = servicos.listar_repositorios(self.get_object())
        except servicos.ErroDePlataforma as erro:
            return _erro(erro)
        return Response([asdict(r) for r in repos])
