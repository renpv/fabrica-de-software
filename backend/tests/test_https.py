"""HTTPS atrás do proxy: a origem do CSRF e o cabeçalho do proxy vêm de FABRICA_URL_PUBLICA."""

import importlib

import pytest
from django.test import Client, override_settings

import config.settings as modulo_settings


def _recarregar(monkeypatch, url):
    monkeypatch.setenv("FABRICA_URL_PUBLICA", url)
    try:
        return importlib.reload(modulo_settings)
    finally:
        monkeypatch.undo()


@pytest.fixture(autouse=True)
def _restaurar_settings():
    yield
    importlib.reload(modulo_settings)


def test_url_http_mantem_o_comportamento_de_desenvolvimento(monkeypatch):
    s = _recarregar(monkeypatch, "http://localhost:8000")
    assert s.CSRF_TRUSTED_ORIGINS == ["http://localhost:8000"]
    assert getattr(s, "SECURE_PROXY_SSL_HEADER", None) is None
    assert s.CSRF_COOKIE_SECURE is False
    assert s.SESSION_COOKIE_SECURE is False


def test_url_https_liga_proxy_ssl_e_cookies_seguros(monkeypatch):
    s = _recarregar(monkeypatch, "https://fabrica.exemplo.com/")
    assert s.CSRF_TRUSTED_ORIGINS == ["https://fabrica.exemplo.com"]
    assert s.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert s.CSRF_COOKIE_SECURE is True
    assert s.SESSION_COOKIE_SECURE is True


def test_login_por_https_atras_do_proxy_passa_no_csrf(monkeypatch, membro_factory):
    s = _recarregar(monkeypatch, "https://fabrica.exemplo.com")
    membro_factory(usuario__username="renato", senha="s3nha-forte")
    cliente = Client(enforce_csrf_checks=True)
    with override_settings(
        ALLOWED_HOSTS=["fabrica.exemplo.com"],
        CSRF_TRUSTED_ORIGINS=s.CSRF_TRUSTED_ORIGINS,
        SECURE_PROXY_SSL_HEADER=s.SECURE_PROXY_SSL_HEADER,
        CSRF_COOKIE_SECURE=s.CSRF_COOKIE_SECURE,
        SESSION_COOKIE_SECURE=s.SESSION_COOKIE_SECURE,
    ):
        extra = {
            "HTTP_HOST": "fabrica.exemplo.com",
            "HTTP_X_FORWARDED_PROTO": "https",
            "HTTP_ORIGIN": "https://fabrica.exemplo.com",
        }
        cliente.get("/api/sessao/", **extra)
        token = cliente.cookies["csrftoken"].value
        r = cliente.post(
            "/api/sessao/",
            {"usuario": "renato", "senha": "s3nha-forte"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
            **extra,
        )
    assert r.status_code == 200


def test_login_por_https_sem_a_configuracao_e_recusado(membro_factory):
    membro_factory(usuario__username="renato", senha="s3nha-forte")
    cliente = Client(enforce_csrf_checks=True)
    extra = {"HTTP_HOST": "fabrica.exemplo.com", "HTTP_ORIGIN": "https://fabrica.exemplo.com"}
    with override_settings(ALLOWED_HOSTS=["fabrica.exemplo.com"], CSRF_TRUSTED_ORIGINS=[]):
        cliente.get("/api/sessao/", **extra)
        token = cliente.cookies["csrftoken"].value
        r = cliente.post(
            "/api/sessao/",
            {"usuario": "renato", "senha": "s3nha-forte"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
            **extra,
        )
    assert r.status_code == 403
