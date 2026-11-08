from rest_framework import serializers, viewsets

from apps.donos.mixins import EscopoDoDonoMixin

from .models import Anotacao


class AnotacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anotacao
        fields = ["id", "texto"]


class AnotacaoViewSet(EscopoDoDonoMixin, viewsets.ModelViewSet):
    queryset = Anotacao.objects.all()
    serializer_class = AnotacaoSerializer
