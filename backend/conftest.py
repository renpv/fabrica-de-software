"""Configuração compartilhada dos testes (fixtures globais entram aqui)."""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.donos.models import Dono, Membro


@pytest.fixture
def membro_factory(db):
    """Cria usuário, dono e membro. `usuario__username` e `senha` trocam os padrões."""
    contador = {"n": 0}

    def criar(usuario__username=None, senha="s3nha-forte", dono=None, nome_do_dono=None):
        contador["n"] += 1
        n = contador["n"]
        usuario = get_user_model().objects.create_user(
            username=usuario__username or f"usuario{n}", password=senha
        )
        dono = dono or Dono.objects.create(nome=nome_do_dono or f"Dono {n}")
        return Membro.objects.create(usuario=usuario, dono=dono)

    return criar


@pytest.fixture(autouse=True)
def _limpa_cache():
    """O limite de tentativas de login usa o cache; cada teste começa do zero."""
    cache.clear()
