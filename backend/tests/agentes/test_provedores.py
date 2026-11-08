import httpx
import pytest
import respx

from apps.agentes import servicos
from apps.agentes.provedores import REGISTRO, obter_provedor

URL_ME = "https://api.cursor.com/v1/me"


@respx.mock
def test_cursor_ok_mostra_quem_conectou():
    respx.get(URL_ME).respond(200, json={"apiKeyName": "fabrica", "userEmail": "r@x.com"})
    r = obter_provedor("cursor").testar({"api_key": "k"}, {})
    assert r.ok and r.status == "ok" and r.mensagem == "Conectado como r@x.com."


@respx.mock
def test_cursor_sem_email_usa_o_nome_da_chave():
    respx.get(URL_ME).respond(200, json={"apiKeyName": "fabrica"})
    r = obter_provedor("cursor").testar({"api_key": "k"}, {})
    assert r.ok and r.mensagem == "Conectado como fabrica."


@respx.mock
@pytest.mark.parametrize("codigo", [401, 403])
def test_cursor_chave_recusada(codigo):
    respx.get(URL_ME).respond(codigo)
    r = obter_provedor("cursor").testar({"api_key": "k"}, {})
    assert not r.ok and r.status == "falha"
    assert (
        r.mensagem
        == "A chave foi recusada pelo Cursor. Gere uma nova no painel do Cursor e cole aqui."
    )


@respx.mock
def test_cursor_fora_do_ar():
    respx.get(URL_ME).mock(side_effect=httpx.ConnectTimeout("lento"))
    r = obter_provedor("cursor").testar({"api_key": "k"}, {})
    assert not r.ok and r.status == "falha"
    assert r.mensagem == "Não consegui falar com o Cursor agora. Tente de novo em instantes."


@respx.mock
def test_cursor_erro_de_conexao():
    respx.get(URL_ME).mock(side_effect=httpx.ConnectError("sem rede"))
    r = obter_provedor("cursor").testar({"api_key": "k"}, {})
    assert r.status == "falha" and r.mensagem.startswith("Não consegui falar com o Cursor")


@respx.mock
@pytest.mark.parametrize("codigo", [429, 500, 503])
def test_cursor_outro_erro_http_explica_o_que_fazer(codigo):
    respx.get(URL_ME).respond(codigo)
    r = obter_provedor("cursor").testar({"api_key": "k"}, {})
    assert not r.ok and r.status == "falha"
    assert r.mensagem == f"O Cursor respondeu com erro (HTTP {codigo}). Tente de novo em instantes."


@respx.mock
def test_cursor_envia_chave_limpa():
    rota = respx.get(URL_ME).respond(200, json={"apiKeyName": "a"})
    servicos.testar_dados("cursor", {"api_key": "  k123\n"}, {})
    assert rota.calls.last.request.headers["Authorization"] == "Bearer k123"


def test_cursor_usa_timeout_de_10_segundos():
    with respx.mock:
        rota = respx.get(URL_ME).respond(200, json={"apiKeyName": "a"})
        obter_provedor("cursor").testar({"api_key": "k"}, {})
    assert rota.calls.last.request.extensions["timeout"]["connect"] == 10


def test_limpar_credenciais_so_tira_as_pontas():
    limpo = servicos.limpar_credenciais("cursor", {"a": " \n x\ny \n", "b": "z"})
    assert limpo == {"a": "x\ny", "b": "z"}


def test_cursor_guia_aponta_para_o_painel():
    links = [p.link for p in obter_provedor("cursor").guia]
    assert "https://cursor.com/dashboard/api" in links


def test_claude_local_aguarda_runner():
    r = obter_provedor("claude_local").testar({}, {"rotulo_maquina": "PC"})
    assert r.ok is False and r.status == "aguardando_runner"
    assert r.mensagem == "Esta conta fica pronta quando o runner do seu PC se conectar."


def test_tipo_desconhecido():
    with pytest.raises(ValueError, match="Tipo de agente desconhecido: xpto"):
        obter_provedor("xpto")


def test_etiqueta_e_modelos_dos_provedores():
    assert (
        obter_provedor("claude_local").etiqueta == "claude"
        and obter_provedor("cursor").etiqueta == "cursor"
    )
    assert obter_provedor("claude_local").modelos_sugeridos == ["opus", "sonnet", "haiku"]
    assert obter_provedor("cursor").modelos_sugeridos == []


def test_registro_tem_os_dois_tipos():
    assert set(REGISTRO) == {"cursor", "claude_local"}
    assert all(p.tipo == t for t, p in REGISTRO.items())
