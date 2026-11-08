from rest_framework import serializers

from .models import ConexaoPlataforma


class ConexaoPlataformaSerializer(serializers.ModelSerializer):
    """Leitura da conexão. As credenciais nunca saem: só `tem_credenciais`."""

    tem_credenciais = serializers.SerializerMethodField()

    class Meta:
        model = ConexaoPlataforma
        fields = [
            "id", "nome", "tipo", "url_base", "config", "status",
            "ultimo_teste_mensagem", "tem_credenciais",
        ]  # fmt: skip
        read_only_fields = fields

    def get_tem_credenciais(self, conexao) -> bool:
        return bool(conexao.credenciais)


class ManifestoPedidoSerializer(serializers.Serializer):
    # O GitHub limita o nome do App a 34 caracteres; o prefixo "Fabrica " ocupa 8.
    nome = serializers.CharField(
        max_length=26,
        error_messages={
            "max_length": "Use até 26 caracteres: o GitHub limita o nome do App a 34 e a "
            "central acrescenta «Fabrica » na frente."
        },
    )


class ManifestoRespostaSerializer(serializers.Serializer):
    acao = serializers.URLField()
    manifesto = serializers.DictField()


class RetornoGitHubSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=200)
    state = serializers.CharField(max_length=2000)


class InstaladoGitHubSerializer(serializers.Serializer):
    installation_id = serializers.CharField(max_length=20)
    state = serializers.CharField(max_length=2000)


class RepositorioSerializer(serializers.Serializer):
    id_externo = serializers.CharField()
    caminho = serializers.CharField()
    url_web = serializers.CharField()


class TesteDaConexaoSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    status = serializers.CharField()
    mensagem = serializers.CharField()


class ErroSerializer(serializers.Serializer):
    detail = serializers.CharField()
