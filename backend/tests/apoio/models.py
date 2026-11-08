from django.db import models

from apps.donos.models import PertenceADono


class Anotacao(PertenceADono):
    """Entidade concreta só para os testes de isolamento por dono."""

    texto = models.CharField(max_length=200)
