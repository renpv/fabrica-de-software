from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
import respx
from django.core import signing

from apps.plataformas.models import ConexaoPlataforma

API = "https://api.github.com"
URL_CONVERSAO = f"{API}/app-manifests/CODIGO123/conversions"
BASE = "/api/conexoes-plataforma/"
SEGREDOS = ["wh-secreto-xyz", "cs-secreto-xyz", "Iv1.abc"]


@pytest.fixture
def logado(client, membro_factory):
    membro = membro_factory()
    client.force_login(membro.usuario)
    return membro


def _json(client, metodo, url, corpo=None):
    return getattr(client, metodo)(url, corpo, content_type="application/json")


def _state(client, nome="Central"):
    r = _json(client, "post", f"{BASE}github/manifesto/", {"nome": nome})
    assert r.status_code == 200, r.content
    acao = r.json()["acao"]
    return parse_qs(urlparse(acao).query)["state"][0]


def _conversao(pem, **extra):
    return {
        "id": 321, "slug": "fabrica-central", "client_id": "Iv1.abc",
        "client_secret": "cs-secreto-xyz", "webhook_secret": "wh-secreto-xyz",
        "pem": pem, **extra,
    }  # fmt: skip


def test_manifesto_tem_webhook_e_permissoes(client, logado, settings):
    settings.FABRICA_URL_PUBLICA = "https://fabrica.exemplo.com"

    r = _json(client, "post", f"{BASE}github/manifesto/", {"nome": "Central"})

    assert r.status_code == 200
    corpo = r.json()
    url = urlparse(corpo["acao"])
    assert f"{url.scheme}://{url.netloc}{url.path}" == "https://github.com/settings/apps/new"
    state = parse_qs(url.query)["state"][0]
    assert signing.loads(state, salt="plataformas.github.manifesto", max_age=3600)["d"] == str(
        logado.dono.id
    )
    m = corpo["manifesto"]
    assert m["name"] == "Fabrica Central"
    assert m["url"] == "https://fabrica.exemplo.com"
    assert m["hook_attributes"] == {"url": "https://fabrica.exemplo.com/api/webhooks/github/"}
    assert m["redirect_url"] == f"https://fabrica.exemplo.com{BASE}github/retorno/"
    assert m["setup_url"] == f"https://fabrica.exemplo.com{BASE}github/instalado/"
    assert m["public"] is False
    assert m["default_permissions"] == {
        "contents": "write", "issues": "write", "pull_requests": "write",
        "metadata": "read", "checks": "read", "actions": "read",
    }  # fmt: skip
    assert m["default_events"] == [
        "issues", "issue_comment", "pull_request", "pull_request_review", "check_suite",
    ]  # fmt: skip


def test_manifesto_exige_login_e_nome(client, logado):
    assert _json(client, "post", f"{BASE}github/manifesto/", {"nome": "  "}).status_code == 400
    client.logout()
    assert _json(client, "post", f"{BASE}github/manifesto/", {"nome": "x"}).status_code == 403


@respx.mock
def test_retorno_converte_e_grava_cifrado(client, logado, chaves_rsa):
    rota = respx.post(URL_CONVERSAO).respond(201, json=_conversao(chaves_rsa[0]))
    state = _state(client)

    r = client.get(f"{BASE}github/retorno/", {"code": "CODIGO123", "state": state})

    assert r.status_code == 302
    destino = urlparse(r["Location"])
    assert f"{destino.scheme}://{destino.netloc}{destino.path}" == (
        "https://github.com/apps/fabrica-central/installations/new"
    )
    state_instalacao = parse_qs(destino.query)["state"][0]
    conexao = ConexaoPlataforma.objects.get()
    carga = signing.loads(state_instalacao, salt="plataformas.github.instalacao", max_age=3600)
    assert carga["d"] == str(logado.dono.id) and carga["c"] == str(conexao.id)
    assert (conexao.dono, conexao.tipo, conexao.nome) == (logado.dono, "github", "Central")
    assert conexao.credenciais["app_id"] == "321"
    assert conexao.credenciais["slug"] == "fabrica-central"
    assert conexao.credenciais["webhook_secret"] == "wh-secreto-xyz"
    assert conexao.config == {}
    assert rota.call_count == 1
    # no banco o texto está cifrado
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("select credenciais from plataformas_conexaoplataforma")
        bruto = cur.fetchone()[0]
    assert "wh-secreto-xyz" not in bruto and "BEGIN" not in bruto


@respx.mock
def test_pem_mantem_quebras_internas(client, logado, chaves_rsa):
    pem = chaves_rsa[0]
    assert pem.count("\n") > 3
    respx.post(URL_CONVERSAO).respond(201, json=_conversao("\n" + pem + "\n  "))
    state = _state(client)

    r = client.get(f"{BASE}github/retorno/", {"code": "CODIGO123", "state": state})

    assert r.status_code == 302
    salvo = ConexaoPlataforma.objects.get().credenciais["pem"]
    assert salvo == pem.strip()
    assert salvo.count("\n") == pem.strip().count("\n")
    jwt.encode({"iss": "1"}, salvo, algorithm="RS256")  # continua sendo uma chave válida


@respx.mock
def test_retorno_com_state_invalido_da_400(client, logado, chaves_rsa):
    rota = respx.post(URL_CONVERSAO).respond(201, json=_conversao(chaves_rsa[0]))

    for state in ["lixo", "", signing.dumps({"d": str(logado.dono.id)}, salt="outro-sal")]:
        r = client.get(f"{BASE}github/retorno/", {"code": "CODIGO123", "state": state})
        assert r.status_code == 400, state
        assert "detail" in r.json()
    assert not rota.called
    assert not ConexaoPlataforma.objects.exists()


@respx.mock
def test_retorno_com_state_de_outro_dono_da_400(client, logado, chaves_rsa, db):
    from apps.donos.models import Dono

    rota = respx.post(URL_CONVERSAO).respond(201, json=_conversao(chaves_rsa[0]))
    alheio = signing.dumps(
        {"d": str(Dono.objects.create(nome="Outro").id), "n": "x", "nm": "Z"},
        salt="plataformas.github.manifesto",
    )

    r = client.get(f"{BASE}github/retorno/", {"code": "CODIGO123", "state": alheio})

    assert r.status_code == 400
    assert not rota.called and not ConexaoPlataforma.objects.exists()


@respx.mock
def test_retorno_com_state_expirado_da_400(client, logado, chaves_rsa, monkeypatch):
    rota = respx.post(URL_CONVERSAO).respond(201, json=_conversao(chaves_rsa[0]))
    state = _state(client)
    from apps.plataformas import servicos

    monkeypatch.setattr(servicos, "VALIDADE_STATE_SEGUNDOS", -1)

    r = client.get(f"{BASE}github/retorno/", {"code": "CODIGO123", "state": state})

    assert r.status_code == 400 and not rota.called


@respx.mock
def test_retorno_sem_login_ou_sem_dono_recusa(client, logado, chaves_rsa, django_user_model):
    rota = respx.post(URL_CONVERSAO).respond(201, json=_conversao(chaves_rsa[0]))
    state = _state(client)
    client.logout()
    assert (
        client.get(f"{BASE}github/retorno/", {"code": "CODIGO123", "state": state}).status_code
        == 403
    )
    sem_dono = django_user_model.objects.create_user(username="semdono", password="x-x-x-x-x1")
    client.force_login(sem_dono)
    assert (
        client.get(f"{BASE}github/retorno/", {"code": "CODIGO123", "state": state}).status_code
        == 403
    )
    assert not rota.called


@respx.mock
def test_retorno_codigo_com_caracteres_estranhos_da_400(client, logado):
    state = _state(client)
    r = client.get(f"{BASE}github/retorno/", {"code": "../../x?y=1", "state": state})
    assert r.status_code == 400 and not ConexaoPlataforma.objects.exists()


@respx.mock
def test_retorno_erros_do_github_viram_mensagem_sem_segredo(client, logado, chaves_rsa):
    state = _state(client)
    casos = [
        httpx.Response(404, json={"message": "Not Found " + chaves_rsa[0]}),
        httpx.Response(500, text=chaves_rsa[0]),
        httpx.Response(201, json={"id": 1, "slug": "../evil", "pem": chaves_rsa[0]}),
        httpx.Response(201, json=_conversao(chaves_rsa[0], slug="Slug Invalido/x")),
        httpx.Response(201, text="nao e json " + chaves_rsa[0]),
        httpx.ConnectTimeout("lento"),
    ]
    for caso in casos:
        respx.post(URL_CONVERSAO).mock(side_effect=caso if isinstance(caso, Exception) else [caso])
        r = client.get(f"{BASE}github/retorno/", {"code": "CODIGO123", "state": state})
        assert r.status_code in (400, 502), (caso, r.status_code)
        assert "BEGIN" not in r.content.decode()
        assert "detail" in r.json()
        assert not ConexaoPlataforma.objects.exists()


def _conexao_para_instalar(client, chaves_rsa):
    with respx.mock:
        respx.post(URL_CONVERSAO).respond(201, json=_conversao(chaves_rsa[0]))
        state = _state(client)
        r = client.get(f"{BASE}github/retorno/", {"code": "CODIGO123", "state": state})
    return parse_qs(urlparse(r["Location"]).query)["state"][0], ConexaoPlataforma.objects.get()


@respx.mock
def test_instalado_grava_installation_id(client, logado, chaves_rsa, settings):
    settings.FABRICA_URL_PUBLICA = "https://fabrica.exemplo.com/"
    state, conexao = _conexao_para_instalar(client, chaves_rsa)
    rota = respx.get(f"{API}/app/installations/555").respond(200, json={"id": 555, "app_id": 321})

    r = client.get(f"{BASE}github/instalado/", {"installation_id": "555", "state": state})

    assert r.status_code == 302
    assert r["Location"] == "https://fabrica.exemplo.com/plataformas"
    conexao.refresh_from_db()
    assert conexao.config["installation_id"] == "555"
    jwt_enviado = rota.calls.last.request.headers["authorization"].removeprefix("Bearer ")
    assert jwt.decode(jwt_enviado, chaves_rsa[1], algorithms=["RS256"])["iss"] == "321"


@respx.mock
def test_instalado_de_outro_app_nao_grava(client, logado, chaves_rsa):
    state, conexao = _conexao_para_instalar(client, chaves_rsa)
    respx.get(f"{API}/app/installations/555").respond(200, json={"id": 555, "app_id": 999})

    r = client.get(f"{BASE}github/instalado/", {"installation_id": "555", "state": state})

    assert r.status_code == 400
    conexao.refresh_from_db()
    assert conexao.config == {}


@respx.mock
def test_instalado_inexistente_ou_com_erro_nao_grava(client, logado, chaves_rsa):
    state, conexao = _conexao_para_instalar(client, chaves_rsa)
    for resposta in [httpx.Response(404, json={}), httpx.Response(500), httpx.ConnectError("x")]:
        respx.get(f"{API}/app/installations/555").mock(
            side_effect=resposta if isinstance(resposta, Exception) else [resposta]
        )
        r = client.get(f"{BASE}github/instalado/", {"installation_id": "555", "state": state})
        assert r.status_code in (400, 502)
        assert "detail" in r.json()
    conexao.refresh_from_db()
    assert conexao.config == {}


@respx.mock
def test_instalado_state_invalido_ou_alheio_ou_id_ruim_da_400(client, logado, chaves_rsa, db):
    from apps.donos.models import Dono

    state, conexao = _conexao_para_instalar(client, chaves_rsa)
    rota = respx.get(f"{API}/app/installations/555").respond(200, json={"app_id": 321})
    alheio = signing.dumps(
        {"d": str(Dono.objects.create(nome="Outro").id), "c": str(conexao.id), "n": "x"},
        salt="plataformas.github.instalacao",
    )
    do_manifesto = signing.dumps(
        {"d": str(logado.dono.id), "c": str(conexao.id), "n": "x"},
        salt="plataformas.github.manifesto",
    )
    for s in ["lixo", alheio, do_manifesto]:
        r = client.get(f"{BASE}github/instalado/", {"installation_id": "555", "state": s})
        assert r.status_code == 400, s
    r = client.get(f"{BASE}github/instalado/", {"installation_id": "5/../x", "state": state})
    assert r.status_code == 400
    assert not rota.called
    conexao.refresh_from_db()
    assert conexao.config == {}


@respx.mock
def test_instalado_conexao_de_outro_dono_da_400(client, logado, chaves_rsa, conexao_github):
    # state assinado para o dono logado, mas apontando para a conexão de outro dono
    state = signing.dumps(
        {"d": str(logado.dono.id), "c": str(conexao_github.id), "n": "x"},
        salt="plataformas.github.instalacao",
    )
    rota = respx.get(f"{API}/app/installations/555").respond(200, json={"app_id": 123})

    r = client.get(f"{BASE}github/instalado/", {"installation_id": "555", "state": state})

    assert r.status_code == 400 and not rota.called
    conexao_github.refresh_from_db()
    assert conexao_github.config == {"installation_id": "777"}


def test_lista_detalhe_e_isolamento(client, logado, conexao_github, chaves_rsa):
    from apps.plataformas.models import ConexaoPlataforma as C

    minha = C.objects.create(
        dono=logado.dono, nome="Minha", tipo="github", credenciais={"app_id": "1"}
    )

    lista = client.get(BASE).json()
    ids = (
        [c["id"] for c in lista] if isinstance(lista, list) else [c["id"] for c in lista["results"]]
    )
    assert ids == [str(minha.id)]
    detalhe = client.get(f"{BASE}{minha.id}/").json()
    assert set(detalhe) == {
        "id", "nome", "tipo", "url_base", "config", "status", "ultimo_teste_mensagem",
        "tem_credenciais",
    }  # fmt: skip
    assert detalhe["tem_credenciais"] is True
    assert client.get(f"{BASE}{conexao_github.id}/").status_code == 404
    assert client.delete(f"{BASE}{conexao_github.id}/").status_code == 404
    assert client.delete(f"{BASE}{minha.id}/").status_code == 204
    assert not C.objects.filter(pk=minha.pk).exists()
    assert client.post(BASE, {"nome": "x"}).status_code == 405


def test_conexoes_exigem_login(client, db):
    assert client.get(BASE).status_code == 403


@respx.mock
def test_testar_e_repositorios_pela_api(client, logado, conexao_github):
    conexao_github.dono = logado.dono
    conexao_github.save()
    respx.post(f"{API}/app/installations/777/access_tokens").respond(201, json={"token": "ghs_x"})
    respx.get(f"{API}/installation/repositories").respond(
        200,
        json={
            "repositories": [{"id": 1, "full_name": "a/b", "html_url": "https://github.com/a/b"}]
        },
    )

    t = client.post(f"{BASE}{conexao_github.id}/testar/")
    r = client.get(f"{BASE}{conexao_github.id}/repositorios/")

    assert t.status_code == 200 and t.json()["ok"] is True
    assert r.json() == [{"id_externo": "1", "caminho": "a/b", "url_web": "https://github.com/a/b"}]
    conexao_github.refresh_from_db()
    assert conexao_github.status == "ok"


@respx.mock
def test_repositorios_com_github_fora_do_ar_da_502_em_ptbr(client, logado, conexao_github):
    conexao_github.dono = logado.dono
    conexao_github.save()
    respx.post(f"{API}/app/installations/777/access_tokens").mock(
        side_effect=httpx.ConnectError("x")
    )
    r = client.get(f"{BASE}{conexao_github.id}/repositorios/")
    assert r.status_code == 502 and "GitHub" in r.json()["detail"]


@respx.mock
def test_resposta_nunca_tem_credenciais(client, logado, chaves_rsa):
    vistas = []

    def conferir(r):
        corpo = r.content.decode()
        for segredo in [*SEGREDOS, "BEGIN", "ghs_token_secreto"]:
            assert segredo not in corpo, (segredo, r.status_code)
        vistas.append(r.status_code)

    respx.post(URL_CONVERSAO).respond(201, json=_conversao(chaves_rsa[0]))
    respx.post(f"{API}/app/installations/555/access_tokens").respond(
        201, json={"token": "ghs_token_secreto"}
    )
    respx.get(f"{API}/app/installations/555").respond(200, json={"app_id": 321})
    respx.get(f"{API}/installation/repositories").respond(200, json={"repositories": []})
    state = _state(client)
    conferir(client.get(f"{BASE}github/retorno/", {"code": "CODIGO123", "state": state}))
    conexao = ConexaoPlataforma.objects.get()
    conexao.config = {"installation_id": "555"}
    conexao.save()
    url = f"{BASE}{conexao.id}/"
    conferir(client.get(BASE))
    conferir(client.get(url))
    conferir(client.post(f"{url}testar/"))
    conferir(client.get(f"{url}repositorios/"))
    conferir(client.get(f"{BASE}github/retorno/", {"code": "CODIGO123", "state": "lixo"}))
    conferir(client.get(f"{BASE}github/retorno/", {"code": "../x", "state": state}))
    conferir(client.get(f"{BASE}github/instalado/", {"installation_id": "555", "state": "lixo"}))
    respx.post(URL_CONVERSAO).respond(404, json={"message": chaves_rsa[0]})
    conferir(client.get(f"{BASE}github/retorno/", {"code": "CODIGO123", "state": _state(client)}))
    assert {200, 302, 400, 502} & set(vistas)
    assert 400 in vistas and 200 in vistas and 302 in vistas
