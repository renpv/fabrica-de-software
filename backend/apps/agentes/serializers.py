from rest_framework import serializers

from apps.donos.models import Cliente

from . import servicos
from .models import ContaAgente


class CampoCadastroSerializer(serializers.Serializer):
    chave = serializers.CharField()
    rotulo = serializers.CharField()
    secreto = serializers.BooleanField()
    ajuda = serializers.CharField()
    obrigatorio = serializers.BooleanField()


class PassoGuiaSerializer(serializers.Serializer):
    texto = serializers.CharField()
    link = serializers.CharField(allow_null=True)


class TipoDeAgenteSerializer(serializers.Serializer):
    tipo = serializers.CharField()
    nome = serializers.CharField()
    etiqueta = serializers.CharField()
    modelos_sugeridos = serializers.ListField(child=serializers.CharField())
    campos = CampoCadastroSerializer(many=True)
    guia = PassoGuiaSerializer(many=True)


class ResultadoTesteSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    status = serializers.CharField()
    mensagem = serializers.CharField()


def _tipo_valido(valor: str) -> str:
    if valor not in {t["tipo"] for t in servicos.listar_tipos()}:
        raise serializers.ValidationError(
            "Tipo de agente desconhecido. Escolha um da lista de tipos de agente."
        )
    return valor


class _ValidaCredenciais:
    # Validação comum de `credenciais` e `config`, sem nunca ecoar valores.

    def _credenciais(self, tipo, credenciais, *, exigir_obrigatorias):
        try:
            return servicos.validar_credenciais(
                tipo, credenciais, exigir_obrigatorias=exigir_obrigatorias
            )
        except ValueError as erro:
            raise serializers.ValidationError({"credenciais": [str(erro)]}) from None

    @staticmethod
    def _config(config):
        if not isinstance(config, dict):
            raise serializers.ValidationError("Envie a configuração como um objeto.")
        return config


class ContaAgenteSerializer(_ValidaCredenciais, serializers.ModelSerializer):
    """Conta de agente. `credenciais` só entra; a leitura devolve `tem_credenciais`."""

    tipo = serializers.CharField()
    # Só de escrita: a leitura devolve apenas `tem_credenciais`.
    credenciais = serializers.JSONField(write_only=True, required=False)
    tem_credenciais = serializers.SerializerMethodField()
    cliente = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.none(), allow_null=True, required=False
    )

    class Meta:
        model = ContaAgente
        fields = [
            "id", "nome", "tipo", "cliente", "config", "limite_simultaneo", "status",
            "ultimo_teste_em", "ultimo_teste_mensagem", "tem_credenciais", "credenciais",
        ]  # fmt: skip
        read_only_fields = ["id", "status", "ultimo_teste_em", "ultimo_teste_mensagem"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pedido = self.context.get("request")
        dono = getattr(pedido, "dono", None)
        if dono is not None and "cliente" in self.fields:
            self.fields["cliente"].queryset = Cliente.objects.filter(dono=dono)

    def get_tem_credenciais(self, conta) -> bool:
        return bool(conta.credenciais)

    def validate_tipo(self, valor):
        _tipo_valido(valor)
        if self.instance is not None and valor != self.instance.tipo:
            raise serializers.ValidationError(
                "O tipo da conta não pode ser trocado. Crie outra conta do tipo desejado."
            )
        return valor

    def validate_config(self, valor):
        return self._config(valor)

    def validate(self, dados):
        if "credenciais" in dados or self.instance is None:
            tipo = self.instance.tipo if self.instance else dados.get("tipo")
            dados["credenciais"] = self._credenciais(
                tipo, dados.get("credenciais", {}), exigir_obrigatorias=self.instance is None
            )
        return dados

    def create(self, validated_data):
        return servicos.criar_conta(validated_data.pop("dono"), validated_data)

    def update(self, instance, validated_data):
        return servicos.atualizar_conta(instance, validated_data)


class TesteDeDadosSerializer(_ValidaCredenciais, serializers.Serializer):
    """Dados de uma conta ainda não salva, para testar a conexão."""

    tipo = serializers.CharField()
    credenciais = serializers.JSONField(write_only=True, required=False)
    config = serializers.JSONField(required=False)

    def validate_tipo(self, valor):
        return _tipo_valido(valor)

    def validate_config(self, valor):
        return self._config(valor)

    def validate(self, dados):
        dados["credenciais"] = self._credenciais(
            dados["tipo"], dados.get("credenciais", {}), exigir_obrigatorias=False
        )
        dados.setdefault("config", {})
        return dados
