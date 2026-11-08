import pytest
import respx

from apps.agentes.models import ContaAgente
from apps.donos.models import Cliente

URL_ME = "https://api.cursor.com/v1/me"
SEGREDO = "segredo-muito-distinto-123"


@pytest.fixture
def logado(client, membro_factory):
    membro = membro_factory()
    client.force_login(membro.usuario)
    return membro


def _json(client, metodo, url, corpo=None):
    return getattr(client, metodo)(url, corpo, content_type="application/json")


def _criar(client, **extra):
    corpo = {"nome": "Minha conta", "tipo": "cursor", "credenciais": {"api_key": SEGREDO}, **extra}
    return _json(client, "post", "/api/contas-agente/", corpo)


def test_tipos_de_agente_lista_cursor_e_claude_local(client, logado):
    r = client.get("/api/tipos-de-agente/")
    assert r.status_code == 200
    tipos = r.json()
    assert [t["tipo"] for t in tipos] == ["claude_local", "cursor"]
    cursor = tipos[1]
    assert set(cursor) == {"tipo", "nome", "etiqueta", "modelos_sugeridos", "campos", "guia"}
    assert cursor["campos"][0] == {
        "chave": "api_key",
        "rotulo": "Chave de API do Cursor",
        "secreto": True,
        "ajuda": "Cole a chave criada no painel do Cursor.",
        "obrigatorio": True,
    }
    assert {"texto", "link"} == set(cursor["guia"][0])


def test_tipos_de_agente_exige_login(client, db):
    assert client.get("/api/tipos-de-agente/").status_code == 403


def test_contas_exigem_login(client, db):
    assert client.get("/api/contas-agente/").status_code == 403
    assert client.get("/api/clientes/").status_code == 403


def test_criar_conta_devolve_so_tem_credenciais(client, logado):
    r = _criar(client)
    assert r.status_code == 201
    corpo = r.json()
    assert set(corpo) == {
        "id", "nome", "tipo", "cliente", "config", "limite_simultaneo", "status",
        "ultimo_teste_em", "ultimo_teste_mensagem", "tem_credenciais",
    }  # fmt: skip
    assert corpo["tem_credenciais"] is True and corpo["status"] == "nao_testada"
    assert ContaAgente.objects.get(id=corpo["id"]).dono == logado.dono


def test_criar_limpa_as_pontas_da_credencial(client, logado):
    r = _criar(client, credenciais={"api_key": " k\n"})
    assert r.status_code == 201
    assert dict(ContaAgente.objects.get(id=r.json()["id"]).credenciais) == {"api_key": "k"}


def test_patch_limpa_as_pontas_e_zera_o_status(client, logado, conta_factory):
    conta = conta_factory(dono=logado.dono, credenciais={"api_key": "velha"}, status="ok")
    r = _json(
        client, "patch", f"/api/contas-agente/{conta.id}/", {"credenciais": {"api_key": " k\n"}}
    )
    assert r.status_code == 200 and r.json()["status"] == "nao_testada"
    conta.refresh_from_db()
    assert dict(conta.credenciais) == {"api_key": "k"} and conta.status == "nao_testada"


def test_patch_sem_credenciais_mantem(client, logado, conta_factory):
    conta = conta_factory(dono=logado.dono, credenciais={"api_key": "guardada"}, status="ok")
    r = _json(client, "patch", f"/api/contas-agente/{conta.id}/", {"nome": "Novo nome"})
    assert r.status_code == 200 and r.json()["nome"] == "Novo nome"
    conta.refresh_from_db()
    assert dict(conta.credenciais) == {"api_key": "guardada"} and conta.status == "ok"


def test_patch_nao_muda_o_tipo(client, logado, conta_factory):
    conta = conta_factory(dono=logado.dono, tipo="cursor")
    r = _json(client, "patch", f"/api/contas-agente/{conta.id}/", {"tipo": "claude_local"})
    assert r.status_code == 400
    assert "tipo" in r.json() and "não pode ser trocado" in r.json()["tipo"][0]
    ok = _json(client, "patch", f"/api/contas-agente/{conta.id}/", {"tipo": "cursor"})
    assert ok.status_code == 200


def test_tipo_desconhecido_da_400(client, logado):
    r = _criar(client, tipo="inexistente")
    assert r.status_code == 400 and "tipo" in r.json()


@pytest.mark.parametrize("credenciais", ["texto", ["a"], {"api_key": 1}, {"api_key": None}])
def test_credenciais_de_formato_errado_da_400(client, logado, credenciais):
    r = _criar(client, credenciais=credenciais)
    assert r.status_code == 400 and "credenciais" in r.json()


def test_criar_exige_segredo_obrigatorio(client, logado):
    r = _criar(client, credenciais={"api_key": "  \n"})
    assert r.status_code == 400
    assert "Chave de API do Cursor" in r.json()["credenciais"][0]
    assert _criar(client, credenciais={}).status_code == 400


def test_credencial_desconhecida_da_400_citando_a_chave(client, logado):
    r = _criar(client, credenciais={"api_key": SEGREDO, "outra": "valor-x"})
    assert r.status_code == 400
    assert "outra" in r.json()["credenciais"][0]
    assert "valor-x" not in r.content.decode() and SEGREDO not in r.content.decode()


def test_conta_de_outro_dono_da_404(client, logado, conta_factory):
    alheia = conta_factory()
    url = f"/api/contas-agente/{alheia.id}/"
    assert client.get(url).status_code == 404
    assert _json(client, "patch", url, {"nome": "x"}).status_code == 404
    assert client.delete(url).status_code == 404
    assert client.post(f"{url}testar/").status_code == 404
    assert client.get("/api/contas-agente/").json() == []


def test_conta_com_cliente_de_outro_dono_da_400(client, logado, membro_factory):
    do_outro = Cliente.objects.create(dono=membro_factory().dono, nome="Alheio")
    r = _criar(client, cliente=str(do_outro.id))
    assert r.status_code == 400 and "cliente" in r.json()
    meu = Cliente.objects.create(dono=logado.dono, nome="Meu")
    assert _criar(client, cliente=str(meu.id)).status_code == 201


def test_excluir_conta(client, logado, conta_factory):
    conta = conta_factory(dono=logado.dono)
    assert client.delete(f"/api/contas-agente/{conta.id}/").status_code == 204
    assert not ContaAgente.objects.filter(id=conta.id).exists()


@respx.mock
def test_testar_sem_salvar_nao_cria_registro(client, logado):
    respx.get(URL_ME).respond(200, json={"userEmail": "r@x.com"})
    r = _json(
        client, "post", "/api/contas-agente/testar/",
        {"tipo": "cursor", "credenciais": {"api_key": " k\n"}, "config": {}},
    )  # fmt: skip
    assert r.status_code == 200
    assert r.json() == {"ok": True, "status": "ok", "mensagem": "Conectado como r@x.com."}
    assert respx.calls.last.request.headers["Authorization"] == "Bearer k"
    assert ContaAgente.objects.count() == 0


@respx.mock
def test_testar_conta_grava_o_status(client, logado, conta_factory):
    respx.get(URL_ME).respond(401)
    conta = conta_factory(dono=logado.dono, credenciais={"api_key": "k"})
    r = client.post(f"/api/contas-agente/{conta.id}/testar/")
    assert r.status_code == 200 and r.json()["ok"] is False and r.json()["status"] == "falha"
    conta.refresh_from_db()
    assert conta.status == "falha" and conta.ultimo_teste_em is not None


@respx.mock
def test_resposta_nunca_tem_credenciais(client, logado):
    respx.get(URL_ME).respond(200, json={"userEmail": "r@x.com"})
    vistas = []

    def conferir(r):
        corpo = r.content.decode()
        assert SEGREDO not in corpo, r.request["PATH_INFO"]
        assert "credenciais" not in r.json() if isinstance(r.json(), dict) else True
        vistas.append(r.status_code)

    criada = _criar(client)
    conferir(criada)
    url = f"/api/contas-agente/{criada.json()['id']}/"
    conferir(client.get("/api/contas-agente/"))
    conferir(client.get(url))
    conferir(_json(client, "patch", url, {"credenciais": {"api_key": SEGREDO + "2"}}))
    conferir(client.post(f"{url}testar/"))
    conferir(_json(
        client, "post", "/api/contas-agente/testar/",
        {"tipo": "cursor", "credenciais": {"api_key": SEGREDO}, "config": {}},
    ))  # fmt: skip
    conferir(_criar(client, nome="", limite_simultaneo="abc"))
    conferir(_criar(client, tipo="inexistente"))
    conferir(_criar(client, cliente="nao-e-uuid"))
    conferir(
        _json(
            client,
            "post",
            "/api/contas-agente/testar/",
            {"tipo": "x", "credenciais": {"api_key": SEGREDO}},
        )
    )
    assert 400 in vistas and 201 in vistas and 200 in vistas
