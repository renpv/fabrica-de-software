import uuid

from django.conf import settings
from django.db import models


class Dono(models.Model):
    """Quem possui os dados. Todo registro de domínio pertence a um dono."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=120)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome


class Membro(models.Model):
    """Liga um usuário de login a um dono (um usuário pertence a um só dono)."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membro"
    )
    dono = models.ForeignKey(Dono, on_delete=models.CASCADE, related_name="membros")

    def __str__(self):
        return f"{self.usuario} em {self.dono}"


class PertenceADonoQuerySet(models.QuerySet):
    def do_dono(self, dono):
        return self.filter(dono=dono)


class PertenceADono(models.Model):
    """Base abstrata de toda entidade de domínio: id UUID, dono e datas."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dono = models.ForeignKey(Dono, on_delete=models.CASCADE, related_name="+")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = PertenceADonoQuerySet.as_manager()

    class Meta:
        abstract = True


class Cliente(PertenceADono):
    """Cliente do dono (por exemplo, uma empresa para quem ele desenvolve)."""

    nome = models.CharField(max_length=120)

    def __str__(self):
        return self.nome
