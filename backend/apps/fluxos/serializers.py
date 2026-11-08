from rest_framework import serializers

from apps.agentes.models import ContaAgente

from . import servicos
from .models import Predefinicao


class PredefinicaoSerializer(serializers.ModelSerializer):
    # `etapas` é JSON livre do usuário: a forma é conferida em `validate`, nunca aqui.
    etapas = serializers.JSONField()

    class Meta:
        model = Predefinicao
        fields = ["id", "nome", "descricao", "metodo", "etapas", "merge_autonomo"]
        read_only_fields = ["id"]
        extra_kwargs = {"descricao": {"required": False}, "metodo": {"required": False}}

    def validate(self, attrs):
        dono = getattr(self.context.get("request"), "dono", None)
        if "etapas" in attrs or "metodo" in attrs or self.instance is None:
            atual = self.instance
            metodo = attrs.get("metodo", atual.metodo if atual else "superpowers")
            etapas = attrs.get("etapas", atual.etapas if atual else [])
            erros = servicos.validar_predefinicao(dono, metodo, etapas)
            metodo_erros = [e for e in erros if e.startswith("Método desconhecido")]
            if metodo_erros:
                raise serializers.ValidationError({"metodo": metodo_erros})
            if erros:
                raise serializers.ValidationError({"etapas": erros})
            if "etapas" in attrs:
                attrs["etapas"] = servicos.normalizar_etapas(attrs["etapas"])
        return attrs


class CriarPadraoSerializer(serializers.Serializer):
    executor = serializers.PrimaryKeyRelatedField(queryset=ContaAgente.objects.none())
    revisor = serializers.PrimaryKeyRelatedField(queryset=ContaAgente.objects.none())

    def get_fields(self):
        campos = super().get_fields()
        dono = getattr(self.context.get("request"), "dono", None)
        fila = ContaAgente.objects.filter(dono=dono) if dono else ContaAgente.objects.none()
        campos["executor"].queryset = fila
        campos["revisor"].queryset = fila
        return campos


class DuplicarSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=120)


class RotuloSerializer(serializers.Serializer):
    chave = serializers.CharField()
    rotulo = serializers.CharField()


class EtapasEGatilhosSerializer(serializers.Serializer):
    etapas = RotuloSerializer(many=True)
    gatilhos = RotuloSerializer(many=True)
    metodos = RotuloSerializer(many=True)


class ErroSerializer(serializers.Serializer):
    detail = serializers.CharField()
