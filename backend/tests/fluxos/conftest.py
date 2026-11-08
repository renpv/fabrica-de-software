import pytest

from apps.donos.models import Cliente


@pytest.fixture
def logado(client, membro_factory):
    membro = membro_factory()
    client.force_login(membro.usuario)
    return membro


@pytest.fixture
def dono(logado):
    return logado.dono


@pytest.fixture
def cliente_x(dono):
    return Cliente.objects.create(dono=dono, nome="X")


@pytest.fixture
def cliente_y(dono):
    return Cliente.objects.create(dono=dono, nome="Y")
