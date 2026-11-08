import getpass

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.donos.models import Membro


def _login(client, usuario, senha):
    return client.post(
        "/api/sessao/", {"usuario": usuario, "senha": senha}, content_type="application/json"
    )


def test_login_devolve_o_dono(client, membro_factory):
    membro = membro_factory(usuario__username="renato", senha="s3nha-forte")
    r = _login(client, "renato", "s3nha-forte")
    assert r.status_code == 200
    assert r.json()["usuario"] == "renato"
    assert r.json()["dono"]["id"] == str(membro.dono.id)
    assert r.json()["dono"]["nome"] == membro.dono.nome


def test_login_errado_explica(client, membro_factory):
    membro_factory(usuario__username="renato", senha="s3nha-forte")
    r = _login(client, "renato", "x")
    assert r.status_code == 400 and r.json()["detail"] == "Usuário ou senha incorretos."


def test_login_de_usuario_sem_dono_e_recusado(client, db):
    get_user_model().objects.create_user(username="solto", password="s3nha-forte")
    r = _login(client, "solto", "s3nha-forte")
    assert r.status_code == 400 and r.json()["detail"] == "Usuário ou senha incorretos."


def test_sessao_sem_login_da_403(client, db):
    assert client.get("/api/sessao/").status_code == 403


def test_sessao_logada_devolve_o_dono(client, membro_factory):
    membro = membro_factory(usuario__username="renato", senha="s3nha-forte")
    _login(client, "renato", "s3nha-forte")
    r = client.get("/api/sessao/")
    assert r.status_code == 200
    assert r.json()["dono"]["id"] == str(membro.dono.id)


def test_logout_encerra_a_sessao(client, membro_factory):
    membro_factory(usuario__username="renato", senha="s3nha-forte")
    _login(client, "renato", "s3nha-forte")
    assert client.delete("/api/sessao/").status_code == 204
    assert client.get("/api/sessao/").status_code == 403


def test_login_exige_csrf_quando_o_cliente_o_aplica(membro_factory):
    from django.test import Client

    membro_factory(usuario__username="renato", senha="s3nha-forte")
    c = Client(enforce_csrf_checks=True)
    r = c.post(
        "/api/sessao/",
        {"usuario": "renato", "senha": "s3nha-forte"},
        content_type="application/json",
    )
    assert r.status_code == 403


def test_criar_dono_cria_usuario_dono_e_membro(db, monkeypatch):
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "s3nha-forte")
    call_command("criar_dono", nome="Casa", usuario="renato", email="r@example.com")
    membro = Membro.objects.get(usuario__username="renato")
    assert membro.dono.nome == "Casa"
    assert membro.usuario.email == "r@example.com"
    assert membro.usuario.check_password("s3nha-forte")


def test_criar_dono_recusa_senhas_diferentes(db, monkeypatch):
    respostas = iter(["uma-senha", "outra-senha"])
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": next(respostas))
    with pytest.raises(CommandError, match="não conferem"):
        call_command("criar_dono", nome="Casa", usuario="renato", email="r@example.com")
    assert not Membro.objects.exists()


def test_criar_dono_recusa_usuario_existente(db, monkeypatch, membro_factory):
    membro_factory(usuario__username="renato")
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "s3nha-forte")
    with pytest.raises(CommandError, match="já existe"):
        call_command("criar_dono", nome="Casa", usuario="renato", email="r@example.com")
