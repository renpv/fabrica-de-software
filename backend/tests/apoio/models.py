from django.db import models

from apps.cofre.campos import CampoSecretoJSON
from apps.donos.models import PertenceADono


class Anotacao(PertenceADono):
    """Entidade concreta só para os testes de isolamento por dono."""

    texto = models.CharField(max_length=200)


class RegistroComSegredo(models.Model):
    """Modelo concreto só para os testes do campo cifrado do cofre."""

    credenciais = CampoSecretoJSON(null=True, blank=True)

    def __str__(self):
        return f"RegistroComSegredo {self.pk}"
