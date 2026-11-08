from dataclasses import asdict

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.donos.mixins import EscopoDoDonoMixin
from apps.donos.permissoes import TemDono
from apps.donos.views import SessaoAutenticacao

from . import servicos
from .models import Projeto
from .serializers import (
    ConferenciaSerializer,
    CriarProjetoSerializer,
    ErroSerializer,
    ProjetoSerializer,
)


def _conferencia(projeto, itens) -> Response:
    return Response(
        {"itens": [asdict(i) for i in itens], "conferido_em": projeto.ultima_conferencia_em}
    )


_RESPOSTAS_CONFERENCIA = {200: ConferenciaSerializer, 400: ErroSerializer, 502: ErroSerializer}


class ProjetoViewSet(
    EscopoDoDonoMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Projetos do dono logado. Criam-se por POST (busca o repositório e já prepara)."""

    queryset = Projeto.objects.select_related("conexao", "predefinicao").order_by("nome")
    serializer_class = ProjetoSerializer
    authentication_classes = [SessaoAutenticacao]
    permission_classes = [IsAuthenticated, TemDono]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    @extend_schema(
        request=CriarProjetoSerializer,
        responses={201: ProjetoSerializer, 400: ErroSerializer, 502: ErroSerializer},
    )
    def create(self, request):
        pedido = CriarProjetoSerializer(data=request.data, context={"request": request})
        pedido.is_valid(raise_exception=True)
        dados = pedido.validated_data
        try:
            projeto = servicos.criar_projeto(
                request.dono,
                nome=dados["nome"].strip(),
                conexao=dados["conexao"],
                repositorio_id_externo=dados["repositorio_id_externo"],
                cliente=dados.get("cliente"),
                predefinicao=dados.get("predefinicao"),
            )
        except servicos.ErroDeProjeto as erro:
            return Response({"detail": str(erro)}, status=400)
        except servicos.ErroDePlataforma as erro:
            return Response({"detail": str(erro)}, status=502)
        return Response(ProjetoSerializer(projeto, context={"request": request}).data, status=201)

    def perform_destroy(self, instance):
        servicos.excluir_projeto(instance)

    def _rodar(self, funcao) -> Response:
        projeto = self.get_object()
        try:
            itens = funcao(projeto)
        except servicos.ErroDeProjeto as erro:
            return Response({"detail": str(erro)}, status=400)
        except servicos.ErroDePlataforma as erro:
            return Response({"detail": str(erro)}, status=502)
        return _conferencia(projeto, itens)

    @extend_schema(
        request=None,
        responses={200: ConferenciaSerializer, 400: ErroSerializer, 502: ErroSerializer},
    )
    @action(detail=True, methods=["post"], url_path="conferir")
    def conferir(self, request, pk=None):
        """Confere o repositório (etiquetas, webhook) sem alterar nada."""
        return self._rodar(servicos.conferir_projeto)

    @extend_schema(
        request=None,
        responses={200: ConferenciaSerializer, 400: ErroSerializer, 502: ErroSerializer},
    )
    @action(detail=True, methods=["post"], url_path="preparar")
    def preparar(self, request, pk=None):
        """Cria o que falta no repositório. Pode ser repetido."""
        return self._rodar(servicos.preparar_projeto)
