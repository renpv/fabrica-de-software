from rest_framework import serializers

from apps.donos.models import Cliente
from apps.plataformas.models import ConexaoPlataforma

from .models import Projeto


class ProjetoSerializer(serializers.ModelSerializer):
    """Leitura do projeto. Só `nome`, `cliente` e `ativo` mudam por PATCH."""

    conferencia = serializers.JSONField(source="ultima_conferencia", read_only=True)
    erro_ao_preparar = serializers.CharField(read_only=True)

    class Meta:
        model = Projeto
        fields = [
            "id", "nome", "conexao", "repositorio_caminho", "repositorio_id_externo",
            "repositorio_url", "cliente", "ativo", "conferencia", "ultima_conferencia_em",
            "erro_ao_preparar",
        ]  # fmt: skip
        read_only_fields = [
            "id", "conexao", "repositorio_caminho", "repositorio_id_externo", "repositorio_url",
            "ultima_conferencia_em",
        ]  # fmt: skip

    def get_fields(self):
        campos = super().get_fields()
        _limitar_ao_dono(campos["cliente"], self.context.get("request"), Cliente)
        return campos


def _limitar_ao_dono(campo, request, modelo):
    dono = getattr(request, "dono", None)
    campo.queryset = modelo.objects.filter(dono=dono) if dono else modelo.objects.none()


class CriarProjetoSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=120)
    conexao = serializers.PrimaryKeyRelatedField(queryset=ConexaoPlataforma.objects.none())
    repositorio_id_externo = serializers.CharField(max_length=100)
    cliente = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.none(), required=False, allow_null=True
    )

    def get_fields(self):
        campos = super().get_fields()
        request = self.context.get("request")
        _limitar_ao_dono(campos["conexao"], request, ConexaoPlataforma)
        _limitar_ao_dono(campos["cliente"], request, Cliente)
        return campos


class ItemConferenciaSerializer(serializers.Serializer):
    chave = serializers.CharField()
    titulo = serializers.CharField()
    ok = serializers.BooleanField()
    mensagem = serializers.CharField()
    consertavel = serializers.BooleanField()


class ConferenciaSerializer(serializers.Serializer):
    itens = ItemConferenciaSerializer(many=True)
    conferido_em = serializers.DateTimeField(allow_null=True)


class ErroSerializer(serializers.Serializer):
    detail = serializers.CharField()
