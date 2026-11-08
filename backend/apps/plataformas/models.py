from django.db import models

from apps.cofre.campos import CampoSecretoJSON
from apps.donos.models import PertenceADono


class ConexaoPlataforma(PertenceADono):
    """Conexão com uma plataforma de código (GitHub, GitLab). As credenciais ficam cifradas."""

    class Tipo(models.TextChoices):
        GITHUB = "github", "GitHub"
        GITLAB = "gitlab", "GitLab"

    class Status(models.TextChoices):
        NAO_TESTADA = "nao_testada", "Não testada"
        OK = "ok", "Funcionando"
        FALHA = "falha", "Com falha"

    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    url_base = models.CharField(max_length=200, blank=True, default="")  # vazio no GitHub
    credenciais = CampoSecretoJSON(default=dict)
    config = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NAO_TESTADA)
    ultimo_teste_mensagem = models.CharField(max_length=300, blank=True, default="")

    def __str__(self):
        return f"{self.nome} ({self.tipo})"


class EventoRecebido(PertenceADono):
    """Webhook recebido e verificado, guardado para processamento posterior (Plano 3)."""

    conexao = models.ForeignKey(
        ConexaoPlataforma, on_delete=models.CASCADE, related_name="eventos_recebidos"
    )
    tipo_evento = models.CharField(max_length=100)
    entrega_id = models.CharField(max_length=100)
    payload = models.JSONField()
    recebido_em = models.DateTimeField(auto_now_add=True)
    processado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conexao", "entrega_id"], name="evento_unico_por_conexao_e_entrega"
            )
        ]

    def __str__(self):
        return f"{self.tipo_evento} ({self.entrega_id})"
