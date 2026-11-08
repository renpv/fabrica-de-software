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
from .models import Predefinicao
from .serializers import (
    CriarPadraoSerializer,
    DuplicarSerializer,
    ErroSerializer,
    EtapasEGatilhosSerializer,
    PredefinicaoSerializer,
)


def _recusa(erro: Exception) -> Response:
    return Response({"detail": str(erro)}, status=400)


class EtapasEGatilhosView(APIView):
    authentication_classes = [SessaoAutenticacao]
    permission_classes = [IsAuthenticated, TemDono]

    @extend_schema(responses=EtapasEGatilhosSerializer)
    def get(self, request):
        """Os rótulos em pt-BR das etapas, dos gatilhos e dos métodos."""
        return Response(servicos.rotulos())


class PredefinicaoViewSet(EscopoDoDonoMixin, viewsets.ModelViewSet):
    """Predefinições de fluxo do dono logado."""

    queryset = Predefinicao.objects.order_by("nome")
    serializer_class = PredefinicaoSerializer
    authentication_classes = [SessaoAutenticacao]
    permission_classes = [IsAuthenticated, TemDono]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    @extend_schema(responses={200: PredefinicaoSerializer, 400: ErroSerializer})
    def partial_update(self, request, *args, **kwargs):
        predefinicao = self.get_object()
        serializer = self.get_serializer(predefinicao, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            predefinicao = servicos.atualizar_predefinicao(
                predefinicao, dict(serializer.validated_data)
            )
        except servicos.ErroDePredefinicao as erro:
            return _recusa(erro)
        return Response(self.get_serializer(predefinicao).data)

    @extend_schema(responses={204: None, 400: ErroSerializer})
    def destroy(self, request, *args, **kwargs):
        try:
            servicos.excluir_predefinicao(self.get_object())
        except servicos.ErroDePredefinicao as erro:
            return _recusa(erro)
        return Response(status=204)

    @extend_schema(
        request=CriarPadraoSerializer, responses={201: PredefinicaoSerializer, 400: ErroSerializer}
    )
    @action(detail=False, methods=["post"], url_path="padrao")
    def padrao(self, request):
        """Cria o «Padrão» com a conta que implementa e a que revisa."""
        pedido = CriarPadraoSerializer(data=request.data, context={"request": request})
        pedido.is_valid(raise_exception=True)
        try:
            criada = servicos.criar_padrao(
                request.dono, pedido.validated_data["executor"], pedido.validated_data["revisor"]
            )
        except servicos.ErroDePredefinicao as erro:
            return _recusa(erro)
        return Response(self.get_serializer(criada).data, status=201)

    @extend_schema(
        request=DuplicarSerializer, responses={201: PredefinicaoSerializer, 400: ErroSerializer}
    )
    @action(detail=True, methods=["post"], url_path="duplicar")
    def duplicar(self, request, pk=None):
        """Copia a predefinição com outro nome."""
        pedido = DuplicarSerializer(data=request.data)
        pedido.is_valid(raise_exception=True)
        copia = servicos.duplicar(self.get_object(), pedido.validated_data["nome"].strip())
        return Response(self.get_serializer(copia).data, status=201)
