import hashlib
import hmac
import json
import uuid
from unittest import mock

import pytest
from django.db import IntegrityError

from apps.donos.models import Dono
from apps.plataformas.models import ConexaoPlataforma, EventoRecebido

URL_GITHUB = "/api/webhooks/github/"
SEGREDO = "wh-secreto-xyz"


def _assinar(corpo: bytes, segredo: str = SEGREDO) -> str:
    return "sha256=" + hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest()


def _github(client, payload=None, *, corpo=None, assinatura="auto", evento="push", entrega=None):
    if corpo is None:
        corpo = json.dumps(payload if payload is not None else {"installation": {"id": 777}})
    corpo = corpo.encode() if isinstance(corpo, str) else corpo
    cab = {"HTTP_X_GITHUB_EVENT": evento, "HTTP_X_GITHUB_DELIVERY": entrega or str(uuid.uuid4())}
    if assinatura == "auto":
        assinatura = _assinar(corpo)
    if assinatura is not None:
        cab["HTTP_X_HUB_SIGNATURE_256"] = assinatura
    return client.post(URL_GITHUB, corpo, content_type="application/json", **cab)


@pytest.fixture
def conexao_gitlab(db):
    dono = Dono.objects.create(nome="Dono GitLab")
    return ConexaoPlataforma.objects.create(
        dono=dono,
        nome="GL",
        tipo="gitlab",
        url_base="https://gitlab.exemplo.com",
        credenciais={"token": "glpat-x", "webhook_secret": "tok-gitlab"},
    )


def _gitlab(
    client, conexao_id, *, token="tok-gitlab", evento="Push Hook", entrega=None, corpo=None
):
    cab = {"HTTP_X_GITLAB_EVENT": evento, "HTTP_X_GITLAB_EVENT_UUID": entrega or str(uuid.uuid4())}
    if token is not None:
        cab["HTTP_X_GITLAB_TOKEN"] = token
    return client.post(
        f"/api/webhooks/gitlab/{conexao_id}/",
        corpo if corpo is not None else json.dumps({"a": 1}),
        content_type="application/json",
        **cab,
    )


# --- GitHub ---------------------------------------------------------------------------


def test_github_assinatura_valida_grava(client, conexao_github):
    r = _github(client, {"installation": {"id": 777}, "x": 1}, entrega="d-1", evento="push")
    assert r.status_code == 202
    ev = EventoRecebido.objects.get()
    assert ev.conexao == conexao_github
    assert ev.dono == conexao_github.dono
    assert (ev.tipo_evento, ev.entrega_id) == ("push", "d-1")
    assert ev.payload["x"] == 1
    assert ev.processado_em is None


def test_github_assinatura_invalida_nao_grava(client, conexao_github):
    r = _github(client, assinatura=_assinar(b"outro"))
    assert r.status_code == 401
    assert EventoRecebido.objects.count() == 0


def test_github_sem_assinatura_401(client, conexao_github):
    assert _github(client, assinatura=None).status_code == 401
    assert EventoRecebido.objects.count() == 0


@pytest.mark.parametrize("assinatura", ["lixo", "sha256=", "sha256=zz", "sha1=abc", "sha256=é"])
def test_github_assinatura_malformada_nunca_500(client, conexao_github, assinatura):
    r = _github(client, assinatura=assinatura)
    assert r.status_code == 401
    assert EventoRecebido.objects.count() == 0


def test_github_segredo_de_outra_conexao_nao_vale(client, conexao_github):
    assert _github(client, assinatura=_assinar(b"{}", "outro")).status_code == 401


def test_github_reentrega_nao_duplica(client, conexao_github):
    assert _github(client, entrega="d-9").status_code == 202
    r = _github(client, entrega="d-9")
    assert r.status_code == 200
    assert EventoRecebido.objects.count() == 1


def test_github_corrida_de_reentrega_responde_200(client, conexao_github):
    with mock.patch(
        "apps.plataformas.servicos.EventoRecebido.objects.create", side_effect=IntegrityError
    ):
        r = _github(client, entrega="d-corrida")
    assert r.status_code == 200
    assert EventoRecebido.objects.count() == 0


def test_github_instalacao_desconhecida_404(client, conexao_github):
    r = _github(client, {"installation": {"id": 999}})
    assert r.status_code == 404
    assert EventoRecebido.objects.count() == 0


def test_github_installation_created_sem_conexao_202_ignorado(client, conexao_github):
    r = _github(client, {"action": "created", "installation": {"id": 999}}, evento="installation")
    assert r.status_code == 202
    assert EventoRecebido.objects.count() == 0


@pytest.mark.parametrize(
    "corpo", ["não é json", "[1, 2]", "{}", '{"installation": 1}', '{"installation": {"id": null}}']
)
def test_github_corpo_invalido_400(client, conexao_github, corpo):
    r = _github(client, corpo=corpo)
    assert r.status_code == 400
    assert EventoRecebido.objects.count() == 0


def test_github_cabecalhos_ausentes_400(client, conexao_github):
    corpo = b'{"installation": {"id": 777}}'
    r = client.post(
        URL_GITHUB,
        corpo,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=_assinar(corpo),
    )
    assert r.status_code == 400
    assert EventoRecebido.objects.count() == 0


def test_github_corpo_grande_413(client, conexao_github):
    corpo = b'{"installation": {"id": 777}, "p": "' + b"a" * (3 * 1024 * 1024) + b'"}'
    r = _github(client, corpo=corpo)
    assert r.status_code == 413
    assert EventoRecebido.objects.count() == 0


def test_github_sem_csrf_nem_sessao(conexao_github, membro_factory):
    from django.test import Client

    c = Client(enforce_csrf_checks=True)
    c.force_login(membro_factory().usuario)
    assert _github(c).status_code == 202


def test_github_resposta_nao_vaza_segredo(client, conexao_github):
    r = _github(client, assinatura=_assinar(b"x"))
    assert SEGREDO not in r.content.decode()


# --- GitLab ---------------------------------------------------------------------------


def test_gitlab_token_valido_grava(client, conexao_gitlab):
    r = _gitlab(client, conexao_gitlab.id, entrega="u-1")
    assert r.status_code == 202
    ev = EventoRecebido.objects.get()
    assert ev.conexao == conexao_gitlab
    assert ev.dono == conexao_gitlab.dono
    assert (ev.tipo_evento, ev.entrega_id) == ("Push Hook", "u-1")


def test_gitlab_token_errado_401(client, conexao_gitlab):
    assert _gitlab(client, conexao_gitlab.id, token="errado").status_code == 401
    assert EventoRecebido.objects.count() == 0


def test_gitlab_sem_token_401(client, conexao_gitlab):
    assert _gitlab(client, conexao_gitlab.id, token=None).status_code == 401


def test_gitlab_token_nao_ascii_nao_da_500(client, conexao_gitlab):
    assert _gitlab(client, conexao_gitlab.id, token="tökén-ç").status_code == 401
    assert EventoRecebido.objects.count() == 0


def test_gitlab_reentrega_nao_duplica(client, conexao_gitlab):
    assert _gitlab(client, conexao_gitlab.id, entrega="u-5").status_code == 202
    assert _gitlab(client, conexao_gitlab.id, entrega="u-5").status_code == 200
    assert EventoRecebido.objects.count() == 1


def test_gitlab_corrida_de_reentrega_responde_200(client, conexao_gitlab):
    with mock.patch(
        "apps.plataformas.servicos.EventoRecebido.objects.create", side_effect=IntegrityError
    ):
        assert _gitlab(client, conexao_gitlab.id).status_code == 200


def test_gitlab_conexao_desconhecida_404(client, conexao_gitlab):
    assert _gitlab(client, uuid.uuid4()).status_code == 404


def test_gitlab_conexao_github_na_rota_gitlab_404(client, conexao_github):
    assert _gitlab(client, conexao_github.id).status_code == 404


def test_gitlab_id_nao_uuid_404(client, conexao_gitlab):
    assert (
        client.post("/api/webhooks/gitlab/abc/", "{}", content_type="application/json").status_code
        == 404
    )


def test_gitlab_corpo_nao_json_400(client, conexao_gitlab):
    assert _gitlab(client, conexao_gitlab.id, corpo="lixo").status_code == 400
    assert EventoRecebido.objects.count() == 0


def test_gitlab_cabecalhos_ausentes_400(client, conexao_gitlab):
    r = client.post(
        f"/api/webhooks/gitlab/{conexao_gitlab.id}/",
        "{}",
        content_type="application/json",
        HTTP_X_GITLAB_TOKEN="tok-gitlab",
    )
    assert r.status_code == 400


def test_gitlab_corpo_grande_413(client, conexao_gitlab):
    corpo = '{"p": "' + "a" * (3 * 1024 * 1024) + '"}'
    assert _gitlab(client, conexao_gitlab.id, corpo=corpo).status_code == 413
    assert EventoRecebido.objects.count() == 0


def test_github_nul_no_payload_400_sem_gravar(client, conexao_github):
    corpo = '{"installation": {"id": 777}, "t": "a\\u0000b"}'
    assert _github(client, corpo=corpo).status_code == 400
    assert EventoRecebido.objects.count() == 0
