import json

import httpx
import jwt
import pytest
import respx

from apps.plataformas import servicos
from apps.plataformas.adaptadores import obter_adaptador
from apps.plataformas.adaptadores.base import ErroDePlataforma, Repositorio
from apps.plataformas.etiquetas import ETIQUETAS_FIXAS, Etiqueta, etiquetas_de_agentes

API = "https://api.github.com"
URL_TOKEN = f"{API}/app/installations/777/access_tokens"
URL_HOOK = f"{API}/app/hook/config"
URL_WEBHOOK = "https://fabrica.exemplo.com/api/webhooks/github/"
REPO = Repositorio(id_externo="10", caminho="renpv/app", url_web="https://github.com/renpv/app")
ETQ = [Etiqueta("tarefa", "0e8a16", "Tarefa"), Etiqueta("agente:cursor", "5319e7", "Cursor")]


def _token_ok():
    respx.post(URL_TOKEN).respond(201, json={"token": "ghs_instalacao_secreta"})


def _repo_json(n):
    return {"id": n, "full_name": f"renpv/repo{n}", "html_url": f"https://github.com/renpv/repo{n}"}


@respx.mock
def test_token_de_instalacao_usa_jwt_rs256(conexao_github, chaves_rsa):
    rota = respx.post(URL_TOKEN).respond(201, json={"token": "ghs_abc"})

    token = obter_adaptador(conexao_github).token_de_instalacao()

    assert token == "ghs_abc"
    pedido = rota.calls.last.request
    jwt_enviado = pedido.headers["authorization"].removeprefix("Bearer ")
    dados = jwt.decode(
        jwt_enviado, chaves_rsa[1], algorithms=["RS256"], options={"verify_iat": False}
    )
    assert dados["iss"] == "123"
    assert dados["exp"] - dados["iat"] == 600
    assert pedido.headers["accept"] == "application/vnd.github+json"
    assert pedido.headers["x-github-api-version"]


@respx.mock
def test_listar_repositorios_percorre_paginas(conexao_github):
    _token_ok()
    pagina2 = f"{API}/installation/repositories?per_page=100&page=2"
    respx.get(f"{API}/installation/repositories", params={"per_page": "100"}).mock(
        side_effect=lambda r: (
            httpx.Response(
                200,
                json={"total_count": 150, "repositories": [_repo_json(n) for n in range(100)]},
                headers={"Link": f'<{pagina2}>; rel="next", <{pagina2}>; rel="last"'},
            )
            if "page=2" not in str(r.url)
            else httpx.Response(
                200,
                json={"total_count": 150, "repositories": [_repo_json(n) for n in range(100, 150)]},
            )
        )
    )

    repos = obter_adaptador(conexao_github).listar_repositorios()

    assert len(repos) == 150
    assert repos[0] == Repositorio("0", "renpv/repo0", "https://github.com/renpv/repo0")
    assert repos[-1].caminho == "renpv/repo149"


@respx.mock
def test_listar_nao_segue_link_para_outro_host(conexao_github):
    _token_ok()
    respx.get(f"{API}/installation/repositories").respond(
        200,
        json={"repositories": [_repo_json(1)]},
        headers={"Link": '<https://malicioso.exemplo/roubo>; rel="next"'},
    )
    desvio = respx.route(host="malicioso.exemplo").respond(200, json={})

    repos = obter_adaptador(conexao_github).listar_repositorios()

    assert len(repos) == 1 and not desvio.called


def _mock_conferencia(*, repos, etiquetas_existentes, hook):
    _token_ok()
    respx.get(f"{API}/installation/repositories").respond(200, json={"repositories": repos})
    respx.get(f"{API}/repos/renpv/app/labels").respond(
        200, json=[{"name": n} for n in etiquetas_existentes]
    )
    respx.get(URL_HOOK).respond(200, json=hook)


HOOK_OK = {"url": URL_WEBHOOK, "content_type": "json", "insecure_ssl": "0", "secret": "********"}


@respx.mock
def test_conferir_aponta_etiquetas_faltando(conexao_github):
    _mock_conferencia(
        repos=[_repo_json(10) | {"full_name": "renpv/app"}],
        etiquetas_existentes=["tarefa"],
        hook=HOOK_OK,
    )

    itens = {i.chave: i for i in obter_adaptador(conexao_github).conferir(REPO, URL_WEBHOOK, ETQ)}

    assert itens["app_instalado_no_repo"].ok
    assert itens["webhook"].ok
    assert not itens["etiquetas"].ok and itens["etiquetas"].consertavel
    assert "agente:cursor" in itens["etiquetas"].mensagem
    assert "tarefa" not in itens["etiquetas"].mensagem


@respx.mock
def test_conferir_app_nao_instalado_no_repo_traz_link(conexao_github):
    _mock_conferencia(repos=[_repo_json(99)], etiquetas_existentes=[], hook=HOOK_OK)

    itens = {i.chave: i for i in obter_adaptador(conexao_github).conferir(REPO, URL_WEBHOOK, ETQ)}

    assert not itens["app_instalado_no_repo"].ok
    assert not itens["app_instalado_no_repo"].consertavel
    assert (
        "https://github.com/apps/fabrica-teste/installations/new"
        in itens["app_instalado_no_repo"].mensagem
    )


@respx.mock
def test_conferir_webhook_com_url_errada(conexao_github):
    _mock_conferencia(
        repos=[_repo_json(10) | {"full_name": "renpv/app"}],
        etiquetas_existentes=["tarefa", "agente:cursor"],
        hook=HOOK_OK | {"url": "https://outro.exemplo/hook"},
    )

    itens = {i.chave: i for i in obter_adaptador(conexao_github).conferir(REPO, URL_WEBHOOK, ETQ)}

    assert not itens["webhook"].ok and itens["webhook"].consertavel
    assert itens["etiquetas"].ok


def test_etiquetas_de_agentes_sem_repeticao():
    etiquetas = etiquetas_de_agentes(["cursor", "claude", "cursor"])

    assert [e.nome for e in etiquetas] == ["agente:claude", "agente:cursor"]
    assert len({e.cor for e in etiquetas}) == 1
    assert all(e.descricao for e in etiquetas)


def test_etiquetas_fixas_cobrem_as_tres_familias():
    nomes = [e.nome for e in ETIQUETAS_FIXAS]
    assert nomes == [
        "acao:implementar", "acao:revisar", "acao:corrigir",
        "em-andamento", "precisa-humano", "tarefa", "melhoria",
    ]  # fmt: skip
    assert all(not e.cor.startswith("#") and len(e.cor) == 6 for e in ETIQUETAS_FIXAS)


@respx.mock
def test_preparar_duas_vezes_nao_duplica(conexao_github):
    _mock_conferencia(
        repos=[_repo_json(10) | {"full_name": "renpv/app"}],
        etiquetas_existentes=[],
        hook=HOOK_OK | {"url": "https://outro.exemplo/hook"},
    )
    criar = respx.post(f"{API}/repos/renpv/app/labels")
    criar.side_effect = [
        httpx.Response(201, json={"name": "tarefa"}),
        httpx.Response(201, json={"name": "agente:cursor"}),
        httpx.Response(  # segunda rodada: já existem
            422,
            json={"message": "Validation Failed", "errors": [{"code": "already_exists"}]},
        ),
        httpx.Response(
            422,
            json={"message": "Validation Failed", "errors": [{"code": "already_exists"}]},
        ),
    ]
    patch = respx.patch(URL_HOOK).respond(200, json=HOOK_OK)
    adaptador = obter_adaptador(conexao_github)

    primeira = adaptador.preparar(REPO, URL_WEBHOOK, ETQ)
    segunda = adaptador.preparar(REPO, URL_WEBHOOK, ETQ)

    assert all(i.ok for i in primeira)
    assert all(i.ok for i in segunda)
    corpo = json.loads(patch.calls.last.request.content)
    assert corpo == {"url": URL_WEBHOOK, "content_type": "json"}
    assert json.loads(criar.calls[0].request.content) == {
        "name": "tarefa", "color": "0e8a16", "description": "Tarefa",
    }  # fmt: skip


@respx.mock
def test_preparar_nao_conserta_app_nao_instalado(conexao_github):
    _mock_conferencia(repos=[_repo_json(99)], etiquetas_existentes=[], hook=HOOK_OK)
    criar = respx.post(f"{API}/repos/renpv/app/labels")

    itens = obter_adaptador(conexao_github).preparar(REPO, URL_WEBHOOK, ETQ)

    assert not criar.called
    assert not next(i for i in itens if i.chave == "app_instalado_no_repo").ok


@respx.mock
def test_testar_com_instalacao_ok(conexao_github):
    _token_ok()
    r = obter_adaptador(conexao_github).testar()
    assert r.ok and r.status == "ok"
    assert "fabrica-teste" in r.mensagem


@respx.mock
def test_testar_sem_instalacao_usa_get_app(conexao_github):
    conexao_github.config = {}
    respx.get(f"{API}/app").respond(200, json={"slug": "fabrica-teste"})
    r = obter_adaptador(conexao_github).testar()
    assert not r.ok and r.status == "falha"
    assert "https://github.com/apps/fabrica-teste/installations/new" in r.mensagem


@respx.mock
def test_testar_credenciais_recusadas(conexao_github):
    respx.post(URL_TOKEN).respond(401, json={"message": "Bad credentials"})
    r = obter_adaptador(conexao_github).testar()
    assert not r.ok and r.status == "falha"
    assert "Bad credentials" not in r.mensagem


@respx.mock
def test_testar_rede_fora_do_ar_vira_mensagem(conexao_github):
    respx.post(URL_TOKEN).mock(side_effect=httpx.ConnectTimeout("lento"))
    r = obter_adaptador(conexao_github).testar()
    assert not r.ok and "GitHub" in r.mensagem


@respx.mock
def test_listar_com_rede_fora_levanta_erro_em_ptbr(conexao_github):
    respx.post(URL_TOKEN).mock(side_effect=httpx.ConnectError("sem rede"))
    with pytest.raises(ErroDePlataforma, match="GitHub"):
        obter_adaptador(conexao_github).listar_repositorios()


def test_pem_invalido_vira_erro_sem_vazar(conexao_github):
    conexao_github.credenciais = conexao_github.credenciais | {"pem": "lixo-secreto-123"}
    with pytest.raises(ErroDePlataforma) as erro:
        obter_adaptador(conexao_github).token_de_instalacao()
    assert "lixo-secreto-123" not in str(erro.value)


@respx.mock
def test_testar_conexao_grava_status(conexao_github):
    _token_ok()
    servicos.testar_conexao(conexao_github)
    conexao_github.refresh_from_db()
    assert conexao_github.status == "ok"
    assert conexao_github.ultimo_teste_mensagem


def test_tipo_desconhecido_levanta_value_error(conexao_github):
    conexao_github.tipo = "bitbucket"
    with pytest.raises(ValueError, match="bitbucket"):
        obter_adaptador(conexao_github)
