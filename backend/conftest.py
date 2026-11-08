"""Configuração compartilhada dos testes (fixtures globais entram aqui)."""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.agentes.models import ContaAgente
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


@pytest.fixture
def conta_factory(db):
    """Cria uma conta de agente. Sem `dono`, cria um dono novo."""
    contador = {"n": 0}

    def criar(dono=None, tipo="cursor", credenciais=None, config=None, nome=None, **extra):
        contador["n"] += 1
        n = contador["n"]
        dono = dono or Dono.objects.create(nome=f"Dono da conta {n}")
        return ContaAgente.objects.create(
            dono=dono,
            nome=nome or f"Conta {n}",
            tipo=tipo,
            credenciais=credenciais if credenciais is not None else {},
            config=config or {},
            **extra,
        )

    return criar


@pytest.fixture(autouse=True)
def _limpa_cache():
    """O limite de tentativas de login usa o cache; cada teste começa do zero."""
    cache.clear()
