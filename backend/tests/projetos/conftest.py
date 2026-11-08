import pytest

from apps.donos.models import Cliente
from apps.plataformas.adaptadores import REGISTRO
from apps.plataformas.adaptadores.base import ErroDePlataforma, ItemConferencia, Repositorio
from apps.plataformas.models import ConexaoPlataforma

REPO = Repositorio("42", "grupo/projeto", "https://git.exemplo.com/grupo/projeto")


class AdaptadorFalso:
    """Adaptador de plataforma sem rede. O estado fica na classe, para o teste inspecionar."""

    repositorios: list[Repositorio] = []
    chamadas: list[tuple] = []
    erro_ao_preparar: bool = False

    def __init__(self, conexao):
        self.conexao = conexao

    def listar_repositorios(self):
        return list(type(self).repositorios)

    def _itens(self):
        return [ItemConferencia("webhook", "Webhook", True, "Webhook configurado.", True)]

    def conferir(self, repo, url_webhook, etiquetas):
        type(self).chamadas.append(("conferir", repo, url_webhook, etiquetas))
        return self._itens()

    def preparar(self, repo, url_webhook, etiquetas):
        if type(self).erro_ao_preparar:
            raise ErroDePlataforma("O GitLab recusou. Tente de novo.")
        type(self).chamadas.append(("preparar", repo, url_webhook, etiquetas))
        return self._itens()


@pytest.fixture
def adaptador_falso(monkeypatch):
    AdaptadorFalso.repositorios = [REPO]
    AdaptadorFalso.chamadas = []
    AdaptadorFalso.erro_ao_preparar = False
    monkeypatch.setitem(REGISTRO, "gitlab", AdaptadorFalso)
    return AdaptadorFalso


@pytest.fixture
def logado(client, membro_factory):
    membro = membro_factory()
    client.force_login(membro.usuario)
    return membro


@pytest.fixture
def conexao(logado):
    return ConexaoPlataforma.objects.create(
        dono=logado.dono,
        nome="GitLab",
        tipo="gitlab",
        url_base="https://git.exemplo.com",
        credenciais={"token": "t", "webhook_secret": "s"},
    )


@pytest.fixture
def cliente_do_dono(logado):
    return Cliente.objects.create(dono=logado.dono, nome="Acme")
