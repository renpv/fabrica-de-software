from apps.donos.models import Cliente, Dono
from apps.plataformas.models import ConexaoPlataforma
from apps.projetos.models import Projeto

BASE = "/api/projetos/"


def _json(client, metodo, url, corpo=None):
    return getattr(client, metodo)(url, corpo, content_type="application/json")


def _corpo(conexao, **extra):
    return {
        "nome": "Meu projeto",
        "conexao": str(conexao.id),
        "repositorio_id_externo": "42",
        **extra,
    }


def test_criar_projeto_ja_prepara(client, logado, conexao, adaptador_falso, cliente_do_dono):
    r = _json(client, "post", BASE, _corpo(conexao, cliente=str(cliente_do_dono.id)))

    assert r.status_code == 201, r.content
    corpo = r.json()
    assert corpo["repositorio_caminho"] == "grupo/projeto"
    assert corpo["cliente"] == str(cliente_do_dono.id)
    assert corpo["conferencia"][0]["chave"] == "webhook"
    assert corpo["erro_ao_preparar"] == ""
    assert adaptador_falso.chamadas[-1][0] == "preparar"
    assert "token" not in r.content.decode()


def test_predefinicao_no_corpo_e_ignorada(client, logado, conexao, adaptador_falso):
    r = _json(client, "post", BASE, _corpo(conexao, predefinicao="qualquer"))
    assert r.status_code == 201
    assert "predefinicao" not in r.json()


def test_repositorio_inacessivel_da_400(client, logado, conexao, adaptador_falso):
    r = _json(client, "post", BASE, _corpo(conexao, repositorio_id_externo="999"))
    assert r.status_code == 400
    assert not Projeto.objects.exists()


def test_conexao_de_outro_dono_da_400(client, logado, adaptador_falso):
    outra = ConexaoPlataforma.objects.create(
        dono=Dono.objects.create(nome="Outro"), nome="x", tipo="gitlab", url_base="https://g"
    )
    r = _json(client, "post", BASE, _corpo(outra))
    assert r.status_code == 400


def test_cliente_de_outro_dono_da_400(client, logado, conexao, adaptador_falso):
    cliente = Cliente.objects.create(dono=Dono.objects.create(nome="Outro"), nome="Alheio")
    r = _json(client, "post", BASE, _corpo(conexao, cliente=str(cliente.id)))
    assert r.status_code == 400


def test_erro_da_plataforma_na_listagem_nao_e_500(
    client, logado, conexao, adaptador_falso, monkeypatch
):
    def falha(self):
        from apps.plataformas.adaptadores.base import ErroDePlataforma

        raise ErroDePlataforma("O GitLab está fora do ar. Tente de novo.")

    monkeypatch.setattr(adaptador_falso, "listar_repositorios", falha)
    r = _json(client, "post", BASE, _corpo(conexao))
    assert r.status_code == 502
    assert r.json()["detail"] == "O GitLab está fora do ar. Tente de novo."


def test_falha_ao_preparar_mantem_projeto_e_devolve_erro(client, logado, conexao, adaptador_falso):
    adaptador_falso.erro_ao_preparar = True
    r = _json(client, "post", BASE, _corpo(conexao))
    assert r.status_code == 201
    assert r.json()["erro_ao_preparar"] == "O GitLab recusou. Tente de novo."
    assert Projeto.objects.count() == 1

    adaptador_falso.erro_ao_preparar = False
    pid = r.json()["id"]
    r2 = _json(client, "post", f"{BASE}{pid}/preparar/")
    assert r2.status_code == 200
    assert r2.json()["itens"][0]["ok"] is True


def test_conferir_e_preparar(client, logado, conexao, adaptador_falso):
    pid = _json(client, "post", BASE, _corpo(conexao)).json()["id"]

    r = _json(client, "post", f"{BASE}{pid}/conferir/")
    assert r.status_code == 200
    assert r.json()["itens"][0]["chave"] == "webhook"
    assert r.json()["conferido_em"]
    assert adaptador_falso.chamadas[-1][0] == "conferir"

    r = _json(client, "post", f"{BASE}{pid}/preparar/")
    assert r.status_code == 200
    assert adaptador_falso.chamadas[-1][0] == "preparar"


def test_erro_da_plataforma_ao_conferir_da_502(
    client, logado, conexao, adaptador_falso, monkeypatch
):
    pid = _json(client, "post", BASE, _corpo(conexao)).json()["id"]

    def falha(self, repo, url, etiquetas):
        from apps.plataformas.adaptadores.base import ErroDePlataforma

        raise ErroDePlataforma("Sem acesso. Tente de novo.")

    monkeypatch.setattr(adaptador_falso, "conferir", falha)
    r = _json(client, "post", f"{BASE}{pid}/conferir/")
    assert r.status_code == 502


def test_projeto_de_outro_dono_da_404(client, logado, adaptador_falso):
    outro = Dono.objects.create(nome="Outro")
    con = ConexaoPlataforma.objects.create(
        dono=outro, nome="x", tipo="gitlab", url_base="https://g"
    )
    projeto = Projeto.objects.create(
        dono=outro, nome="Alheio", conexao=con, repositorio_caminho="a/b",
        repositorio_id_externo="1", repositorio_url="https://g/a/b",
    )  # fmt: skip
    for metodo, url in [
        ("get", f"{BASE}{projeto.id}/"),
        ("patch", f"{BASE}{projeto.id}/"),
        ("delete", f"{BASE}{projeto.id}/"),
        ("post", f"{BASE}{projeto.id}/conferir/"),
        ("post", f"{BASE}{projeto.id}/preparar/"),
    ]:
        assert _json(client, metodo, url, {} if metodo == "patch" else None).status_code == 404
    lista = _json(client, "get", BASE).json()
    assert (lista["results"] if isinstance(lista, dict) else lista) == []


def test_listar_patch_e_excluir(client, logado, conexao, adaptador_falso):
    pid = _json(client, "post", BASE, _corpo(conexao)).json()["id"]

    lista = _json(client, "get", BASE).json()
    itens = lista["results"] if isinstance(lista, dict) else lista
    assert [p["id"] for p in itens] == [pid]

    r = _json(
        client,
        "patch",
        f"{BASE}{pid}/",
        {"nome": "Novo", "ativo": False, "repositorio_caminho": "x/y"},
    )
    assert r.status_code == 200
    assert r.json()["nome"] == "Novo"
    assert r.json()["ativo"] is False
    assert r.json()["repositorio_caminho"] == "grupo/projeto"

    assert _json(client, "delete", f"{BASE}{pid}/").status_code == 204


def test_excluir_conexao_com_projeto_da_409(client, logado, conexao, adaptador_falso):
    _json(client, "post", BASE, _corpo(conexao))
    r = client.delete(f"/api/conexoes-plataforma/{conexao.id}/")
    assert r.status_code == 409
    assert ConexaoPlataforma.objects.filter(pk=conexao.pk).exists()


def test_exige_login(client):
    assert client.get(BASE).status_code in (401, 403)
