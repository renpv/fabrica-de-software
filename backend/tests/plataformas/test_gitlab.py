import json
import logging

import httpx
import pytest
import respx

from apps.donos.models import Dono
from apps.plataformas import servicos
from apps.plataformas.adaptadores import obter_adaptador
from apps.plataformas.adaptadores.base import ErroDePlataforma, Repositorio
from apps.plataformas.etiquetas import ETIQUETAS_FIXAS
from apps.plataformas.models import ConexaoPlataforma

URL = "https://gitlab.unilab.edu.br"
API = f"{URL}/api/v4"
BASE = "/api/conexoes-plataforma/"
TOKEN = "token-de-teste-fake"
MSG_REDE = (
    f"Não consegui acessar {URL}. Confira o endereço e se a central alcança a rede da instância."
)
MSG_SEM_API = "O token precisa do escopo api. Crie outro marcando api."
MSG_RECUSADO = "O GitLab recusou o token. Confira se ele não expirou."


def _dns(*ips):
    def falso(host, porta, *a, **k):
        familia = 10 if ":" in ips[0] else 2
        return [(familia, 1, 6, "", (ip, porta)) for ip in ips]

    return falso


@pytest.fixture(autouse=True)
def dns_publico(monkeypatch):
    """Sem DNS real: por padrão, todo host resolve para um IP público."""
    monkeypatch.setattr("socket.getaddrinfo", _dns("203.0.113.10"))


@pytest.fixture
def logado(client, membro_factory):
    membro = membro_factory()
    client.force_login(membro.usuario)
    return membro


@pytest.fixture
def conexao_gitlab(db):
    dono = Dono.objects.create(nome="Dono do GitLab")
    return ConexaoPlataforma.objects.create(
        dono=dono, nome="GitLab Unilab", tipo="gitlab", url_base=URL,
        credenciais={"token": TOKEN, "webhook_secret": "wh-segredo-abc"},
    )  # fmt: skip


REPO = Repositorio("42", "grupo/projeto", f"{URL}/grupo/projeto")
URL_HOOK = "https://fabrica.exemplo.com/api/webhooks/gitlab/abc/"


def _post(client, corpo):
    return client.post(f"{BASE}gitlab/", corpo, content_type="application/json")


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("gitlab.unilab.edu.br", URL),
        ("https://gitlab.unilab.edu.br/", URL),
        ("https://gitlab.unilab.edu.br/api/v4", URL),
        ("  https://gitlab.unilab.edu.br/api/v4/ ", URL),
        ("http://interno:8080/gitlab/", "http://interno:8080/gitlab"),
    ],
)
def test_normalizar_url(texto, esperado):
    assert servicos.normalizar_url_gitlab(texto) == esperado


@pytest.mark.parametrize(
    "texto", ["", "   ", "ftp://x.com", "https://u:senha@gitlab.com", "https://x.com/?a=1"]
)
def test_normalizar_url_recusa_invalida(texto):
    with pytest.raises(ValueError, match="endereço"):
        servicos.normalizar_url_gitlab(texto)


@respx.mock
def test_testar_ok(conexao_gitlab):
    rota = respx.get(f"{API}/personal_access_tokens/self").respond(
        200, json={"scopes": ["api", "read_user"]}
    )
    r = obter_adaptador(conexao_gitlab).testar()
    assert r.ok and r.status == "ok"
    assert rota.calls.last.request.headers["PRIVATE-TOKEN"] == TOKEN


@respx.mock
def test_token_sem_escopo_api_explica(conexao_gitlab):
    respx.get(f"{API}/personal_access_tokens/self").respond(200, json={"scopes": ["read_api"]})
    r = obter_adaptador(conexao_gitlab).testar()
    assert not r.ok and r.status == "falha" and r.mensagem == MSG_SEM_API


@respx.mock
def test_token_recusado_401(conexao_gitlab):
    respx.get(f"{API}/personal_access_tokens/self").respond(401, json={"message": "x"})
    assert obter_adaptador(conexao_gitlab).testar().mensagem == MSG_RECUSADO


@respx.mock
def test_token_com_quebra_de_linha_e_limpo(client, logado, settings):
    rota = respx.get(f"{API}/personal_access_tokens/self").respond(200, json={"scopes": ["api"]})
    r = _post(client, {"nome": "GL", "url_base": "gitlab.unilab.edu.br", "token": f" {TOKEN}\n"})
    assert r.status_code == 201, r.content
    assert rota.calls.last.request.headers["PRIVATE-TOKEN"] == TOKEN
    conexao = ConexaoPlataforma.objects.get(pk=r.json()["id"])
    assert conexao.credenciais["token"] == TOKEN
    assert len(conexao.credenciais["webhook_secret"]) >= 32
    assert conexao.url_base == URL and conexao.tipo == "gitlab" and conexao.status == "ok"
    assert conexao.dono == logado.dono
    corpo = r.content.decode()
    assert TOKEN not in corpo and conexao.credenciais["webhook_secret"] not in corpo
    assert r.json()["tem_credenciais"] is True and "credenciais" not in r.json()


@respx.mock
@pytest.mark.parametrize("token", ["glpat-é", "glpat-a\nb", "glpat ab", "   "])
def test_token_invalido_da_400_sem_chamar_a_rede(client, logado, token):
    r = _post(client, {"nome": "GL", "url_base": URL, "token": token})
    assert r.status_code == 400
    assert "token" in r.json()["detail"].lower() and "Traceback" not in r.content.decode()
    assert len(respx.calls) == 0
    assert not ConexaoPlataforma.objects.exists()


def test_adaptador_protege_token_nao_ascii(conexao_gitlab):
    conexao_gitlab.credenciais = {"token": "glpat-é"}
    r = obter_adaptador(conexao_gitlab).testar()
    assert not r.ok and "token" in r.mensagem.lower()


@respx.mock
@pytest.mark.parametrize(
    "excecao", [httpx.ConnectError("x"), httpx.ReadTimeout("x"), httpx.RemoteProtocolError("x")]
)
def test_instancia_fora_do_ar_mensagem_clara(client, logado, caplog, excecao):
    respx.get(f"{API}/personal_access_tokens/self").mock(side_effect=excecao)
    with caplog.at_level(logging.DEBUG):
        r = _post(client, {"nome": "GL", "url_base": URL, "token": TOKEN})
    assert r.status_code == 400
    assert r.json() == {"detail": MSG_REDE}
    assert "Traceback" not in r.content.decode()
    assert TOKEN not in caplog.text
    assert not ConexaoPlataforma.objects.exists()


@respx.mock
def test_listar_segue_x_next_page(conexao_gitlab):
    def projeto(i):
        return {"id": i, "path_with_namespace": f"g/p{i}", "web_url": f"{URL}/g/p{i}"}

    rota = respx.get(f"{API}/projects")
    rota.side_effect = lambda req: (
        httpx.Response(200, json=[projeto(1), projeto(2)], headers={"X-Next-Page": "2"})
        if req.url.params.get("page") in (None, "1")
        else httpx.Response(200, json=[projeto(3)], headers={"X-Next-Page": ""})
    )
    repos = obter_adaptador(conexao_gitlab).listar_repositorios()
    assert [r.id_externo for r in repos] == ["1", "2", "3"]
    assert repos[2] == Repositorio("3", "g/p3", f"{URL}/g/p3")
    primeira = rota.calls[0].request.url.params
    assert primeira["membership"] == "true" and primeira["min_access_level"] == "40"
    assert primeira["per_page"] == "100"
    assert len(rota.calls) == 2


@respx.mock
def test_preparar_cria_webhook_com_segredo(conexao_gitlab):
    respx.get(f"{API}/projects/42/labels").respond(200, json=[])
    respx.post(f"{API}/projects/42/labels").respond(201, json={})
    respx.get(f"{API}/projects/42/hooks").respond(200, json=[])
    criar = respx.post(f"{API}/projects/42/hooks").respond(201, json={"id": 1})

    itens = obter_adaptador(conexao_gitlab).preparar(REPO, URL_HOOK, ETIQUETAS_FIXAS)

    corpo = json.loads(criar.calls.last.request.content)
    assert corpo == {
        "url": URL_HOOK, "token": "wh-segredo-abc", "issues_events": True,
        "merge_requests_events": True, "note_events": True, "pipeline_events": True,
        "enable_ssl_verification": True,
    }  # fmt: skip
    assert {i.chave: i.ok for i in itens} == {"etiquetas": True, "webhook": True}
    criadas = [
        c.request
        for c in respx.calls
        if c.request.method == "POST" and "labels" in c.request.url.path
    ]
    assert len(criadas) == len(ETIQUETAS_FIXAS)
    assert json.loads(criadas[0].content)["color"] == "#1d76db"


@respx.mock
def test_preparar_duas_vezes_nao_duplica(conexao_gitlab):
    nomes = [{"name": e.nome} for e in ETIQUETAS_FIXAS]
    respx.get(f"{API}/projects/42/labels").respond(200, json=nomes)
    criar_etiqueta = respx.post(f"{API}/projects/42/labels").respond(201, json={})
    respx.get(f"{API}/projects/42/hooks").respond(200, json=[{"id": 9, "url": URL_HOOK}])
    criar_hook = respx.post(f"{API}/projects/42/hooks").respond(201, json={})

    adaptador = obter_adaptador(conexao_gitlab)
    for _ in range(2):
        itens = adaptador.preparar(REPO, URL_HOOK, ETIQUETAS_FIXAS)
        assert all(i.ok for i in itens)
    assert criar_etiqueta.call_count == 0 and criar_hook.call_count == 0


@respx.mock
def test_etiqueta_409_conta_como_ok(conexao_gitlab):
    respx.get(f"{API}/projects/42/labels").respond(200, json=[])
    respx.post(f"{API}/projects/42/labels").respond(409, json={"message": "exists"})
    respx.get(f"{API}/projects/42/hooks").respond(200, json=[{"url": URL_HOOK}])
    itens = obter_adaptador(conexao_gitlab).preparar(REPO, URL_HOOK, ETIQUETAS_FIXAS)
    assert all(i.ok for i in itens)


@respx.mock
def test_conferir_aponta_o_que_falta(conexao_gitlab):
    respx.get(f"{API}/projects/42/labels").respond(200, json=[{"name": "tarefa"}])
    respx.get(f"{API}/projects/42/hooks").respond(200, json=[{"url": "https://outro/"}])
    itens = {
        i.chave: i
        for i in obter_adaptador(conexao_gitlab).conferir(REPO, URL_HOOK, ETIQUETAS_FIXAS)
    }
    assert not itens["etiquetas"].ok and "acao:implementar" in itens["etiquetas"].mensagem
    assert not itens["webhook"].ok and itens["webhook"].consertavel


def test_url_do_webhook(conexao_gitlab, settings):
    settings.FABRICA_URL_PUBLICA = "https://fabrica.exemplo.com/"
    assert servicos.url_webhook_gitlab(conexao_gitlab) == (
        f"https://fabrica.exemplo.com/api/webhooks/gitlab/{conexao_gitlab.id}/"
    )


@respx.mock
def test_criar_conexao_invalida_nao_grava(client, logado):
    respx.get(f"{API}/personal_access_tokens/self").respond(200, json={"scopes": ["read_api"]})
    r = _post(client, {"nome": "GL", "url_base": URL, "token": TOKEN})
    assert r.status_code == 400
    assert r.json() == {"detail": MSG_SEM_API}
    assert not ConexaoPlataforma.objects.exists()


def test_criar_conexao_exige_login(client, db):
    assert _post(client, {"nome": "GL", "url_base": URL, "token": TOKEN}).status_code in (401, 403)


def test_criar_conexao_url_invalida_da_400(client, logado):
    r = _post(client, {"nome": "GL", "url_base": "ftp://x", "token": TOKEN})
    assert r.status_code == 400 and "endereço" in r.json()["detail"]


@respx.mock
@pytest.mark.parametrize(
    "endereco",
    [
        "localhost", "127.0.0.1", "[::1]", "169.254.169.254", "0.0.0.0", "[::ffff:127.0.0.1]",
        "[fe80::1]", "224.0.0.1",
    ],
)  # fmt: skip
def test_criar_recusa_endereco_interno(client, logado, monkeypatch, endereco):
    ip = endereco.strip("[]").replace("localhost", "127.0.0.1")
    monkeypatch.setattr("socket.getaddrinfo", _dns(ip))
    r = _post(client, {"nome": "GL", "url_base": endereco, "token": TOKEN})
    assert r.status_code == 400
    assert r.json()["detail"].startswith("Esse endereço aponta para a própria central")
    assert len(respx.calls) == 0
    assert not ConexaoPlataforma.objects.exists()


@respx.mock
def test_criar_recusa_host_que_resolve_para_loopback(client, logado, monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", _dns("203.0.113.10", "127.0.0.1"))
    r = _post(client, {"nome": "GL", "url_base": "gitlab.exemplo.com", "token": TOKEN})
    assert r.status_code == 400 and "rede reservada" in r.json()["detail"]
    assert len(respx.calls) == 0


@respx.mock
def test_criar_aceita_rede_privada(client, logado, monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", _dns("10.1.2.3"))
    respx.get("https://git.interno/api/v4/personal_access_tokens/self").respond(
        200, json={"scopes": ["api"]}
    )
    r = _post(client, {"nome": "GL", "url_base": "git.interno", "token": TOKEN})
    assert r.status_code == 201, r.content


def test_falha_de_dns_mantem_mensagem_de_rede(client, logado, monkeypatch):
    def falha(*a, **k):
        raise OSError("sem dns")

    monkeypatch.setattr("socket.getaddrinfo", falha)
    r = _post(client, {"nome": "GL", "url_base": URL, "token": TOKEN})
    assert r.status_code == 400 and r.json() == {"detail": MSG_REDE}


@respx.mock
def test_adaptador_recusa_na_hora_se_dns_mudou(conexao_gitlab, monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", _dns("127.0.0.1"))
    adaptador = obter_adaptador(conexao_gitlab)
    assert "rede reservada" in adaptador.testar().mensagem
    with pytest.raises(ErroDePlataforma, match="rede reservada"):
        adaptador.listar_repositorios()
    assert len(respx.calls) == 0


def test_normalizar_url_longa_demais():
    with pytest.raises(ValueError, match="longo demais"):
        servicos.normalizar_url_gitlab("a" * 190 + ".com.br/gitlab")


def test_criar_url_longa_da_400(client, logado):
    r = _post(client, {"nome": "GL", "url_base": "a" * 195 + ".com", "token": TOKEN})
    assert r.status_code == 400 and "longo demais" in r.json()["detail"]


@respx.mock
def test_etiqueta_com_403_explica(conexao_gitlab):
    respx.get(f"{API}/projects/42/labels").respond(200, json=[])
    respx.post(f"{API}/projects/42/labels").respond(403, json={"message": "corpo-secreto"})
    with pytest.raises(ErroDePlataforma, match="Maintainer") as e:
        obter_adaptador(conexao_gitlab).preparar(REPO, URL_HOOK, ETIQUETAS_FIXAS)
    assert "corpo-secreto" not in str(e.value)


@respx.mock
def test_webhook_422_diz_que_a_instancia_recusou_a_url(conexao_gitlab):
    respx.get(f"{API}/projects/42/hooks").respond(200, json=[])
    respx.post(f"{API}/projects/42/hooks").respond(422, json={"message": "corpo-secreto"})
    nomes = [{"name": e.nome} for e in ETIQUETAS_FIXAS]
    respx.get(f"{API}/projects/42/labels").respond(200, json=nomes)
    with pytest.raises(ErroDePlataforma, match="recusou o endereço do webhook") as e:
        obter_adaptador(conexao_gitlab).preparar(REPO, URL_HOOK, ETIQUETAS_FIXAS)
    assert "fabrica.exemplo.com" in str(e.value) and "corpo-secreto" not in str(e.value)


@respx.mock
def test_webhook_403_explica(conexao_gitlab):
    nomes = [{"name": e.nome} for e in ETIQUETAS_FIXAS]
    respx.get(f"{API}/projects/42/labels").respond(200, json=nomes)
    respx.get(f"{API}/projects/42/hooks").respond(200, json=[])
    respx.post(f"{API}/projects/42/hooks").respond(403, json={})
    with pytest.raises(ErroDePlataforma, match="Maintainer"):
        obter_adaptador(conexao_gitlab).preparar(REPO, URL_HOOK, ETIQUETAS_FIXAS)
