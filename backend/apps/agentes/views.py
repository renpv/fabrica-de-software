from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.donos.mixins import EscopoDoDonoMixin
from apps.donos.permissoes import TemDono
from apps.donos.views import SessaoAutenticacao

from . import servicos
from .models import ContaAgente
from .serializers import (
    ContaAgenteSerializer,
    ResultadoTesteSerializer,
    TesteDeDadosSerializer,
    TipoDeAgenteSerializer,
)


def _resultado(r) -> Response:
    return Response({"ok": r.ok, "status": r.status, "mensagem": r.mensagem})


class TiposDeAgenteView(APIView):
    """Os tipos de agente disponíveis, com os campos de cadastro e o passo a passo."""

    authentication_classes = [SessaoAutenticacao]
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=TipoDeAgenteSerializer(many=True))
    def get(self, request):
        return Response(servicos.listar_tipos())


class ContaAgenteViewSet(EscopoDoDonoMixin, viewsets.ModelViewSet):
    """Contas de agente do dono logado. As credenciais são só de escrita."""

    queryset = ContaAgente.objects.order_by("nome")
    serializer_class = ContaAgenteSerializer
    authentication_classes = [SessaoAutenticacao]
    permission_classes = [IsAuthenticated, TemDono]

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        servicos.excluir_conta(instance)

    @extend_schema(
        request=TesteDeDadosSerializer,
        responses=ResultadoTesteSerializer,
        operation_id="contas_agente_testar_dados",
    )
    @action(detail=False, methods=["post"], url_path="testar")
    def testar_dados(self, request):
        """Testa tipo, credenciais e config sem gravar nada."""
        dados = TesteDeDadosSerializer(data=request.data, context={"request": request})
        dados.is_valid(raise_exception=True)
        v = dados.validated_data
        return _resultado(servicos.testar_dados(v["tipo"], v["credenciais"], v["config"]))

    @extend_schema(
        request=None, responses=ResultadoTesteSerializer, operation_id="contas_agente_testar"
    )
    @action(detail=True, methods=["post"], url_path="testar")
    def testar(self, request, pk=None):
        """Testa a conta salva e grava o resultado nela."""
        return _resultado(servicos.testar_conta(self.get_object()))
