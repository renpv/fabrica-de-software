from django.db import models

from apps.cofre.campos import CampoSecretoJSON
from apps.donos.models import Cliente, PertenceADono

from .provedores import REGISTRO


class ContaAgente(PertenceADono):
    """Uma conta de um agente de IA (Cursor, Claude no PC). As credenciais ficam cifradas."""

    class Status(models.TextChoices):
        NAO_TESTADA = "nao_testada", "Não testada"
        OK = "ok", "Funcionando"
        FALHA = "falha", "Com falha"
        AGUARDANDO_RUNNER = "aguardando_runner", "Aguardando o runner"

    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=40, choices=[(t, p.nome) for t, p in REGISTRO.items()])
    cliente = models.ForeignKey(
        Cliente, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    credenciais = CampoSecretoJSON(default=dict)
    config = models.JSONField(default=dict, blank=True)
    limite_simultaneo = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NAO_TESTADA)
    ultimo_teste_em = models.DateTimeField(null=True, blank=True)
    ultimo_teste_mensagem = models.CharField(max_length=300, blank=True, default="")

    def __str__(self):
        return f"{self.nome} ({self.tipo})"
