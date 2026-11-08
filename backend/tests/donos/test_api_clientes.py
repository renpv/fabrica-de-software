import pytest

from apps.donos.models import Cliente


@pytest.fixture
def logado(client, membro_factory):
    membro = membro_factory()
    client.force_login(membro.usuario)
    return membro


def test_crud_de_clientes(client, logado):
    r = client.post("/api/clientes/", {"nome": "Acme"}, content_type="application/json")
    assert r.status_code == 201 and set(r.json()) == {"id", "nome"}
    url = f"/api/clientes/{r.json()['id']}/"
    assert Cliente.objects.get(id=r.json()["id"]).dono == logado.dono
    assert (
        client.patch(url, {"nome": "Beta"}, content_type="application/json").json()["nome"]
        == "Beta"
    )
    assert [c["nome"] for c in client.get("/api/clientes/").json()] == ["Beta"]
    assert client.delete(url).status_code == 204


def test_cliente_de_outro_dono_da_404(client, logado, membro_factory):
    alheio = Cliente.objects.create(dono=membro_factory().dono, nome="Alheio")
    assert client.get("/api/clientes/").json() == []
    assert client.get(f"/api/clientes/{alheio.id}/").status_code == 404
    assert client.delete(f"/api/clientes/{alheio.id}/").status_code == 404


def test_clientes_exigem_login(client, db):
    assert (
        client.post("/api/clientes/", {"nome": "x"}, content_type="application/json").status_code
        == 403
    )
