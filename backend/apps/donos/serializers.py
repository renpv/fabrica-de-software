from rest_framework import serializers

from . import servicos
from .models import Cliente


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ["id", "nome"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        return servicos.criar_cliente(validated_data["dono"], {"nome": validated_data["nome"]})

    def update(self, instance, validated_data):
        return servicos.atualizar_cliente(instance, validated_data)
