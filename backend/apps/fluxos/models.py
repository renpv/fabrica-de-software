from django.db import models

from apps.donos.models import PertenceADono


class Predefinicao(PertenceADono):
    """Receita de fluxo: quais etapas, quem faz cada uma e o que a dispara.

    `etapas` é uma lista de `{chave, papel, gatilho, temporizador_minutos?}`; a forma é
    validada por `servicos.validar_etapas`.
    """

    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True, default="")
    metodo = models.CharField(max_length=40, default="superpowers")
    etapas = models.JSONField(default=list)
    merge_autonomo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "predefinição"
        verbose_name_plural = "predefinições"

    def __str__(self):
        return self.nome
