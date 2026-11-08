import respx

from apps.agentes import servicos
from apps.agentes.models import ContaAgente


@respx.mock
def test_testar_conta_grava_status(conta_factory):
    respx.get("https://api.cursor.com/v1/me").respond(
        200, json={"apiKeyName": "a", "userEmail": "r@x.com"}
    )
    conta = conta_factory(tipo="cursor", credenciais={"api_key": " k\n"})
    assert conta.status == "nao_testada" and conta.ultimo_teste_em is None

    r = servicos.testar_conta(conta)

    assert r.ok
    conta = ContaAgente.objects.get(pk=conta.pk)
    assert conta.status == "ok"
    assert conta.ultimo_teste_mensagem == "Conectado como r@x.com."
    assert conta.ultimo_teste_em is not None


def test_testar_conta_claude_local_fica_aguardando(conta_factory):
    conta = conta_factory(tipo="claude_local")
    servicos.testar_conta(conta)
    conta.refresh_from_db()
    assert conta.status == "aguardando_runner"


def test_conta_nao_vaza_credenciais_no_repr(conta_factory):
    conta = conta_factory(credenciais={"api_key": "segredo-123"})
    conta.refresh_from_db()
    assert "segredo-123" not in repr(conta)
    assert "segredo-123" not in repr(conta.credenciais)


def test_conta_do_dono(conta_factory):
    a = conta_factory()
    conta_factory()
    assert list(ContaAgente.objects.do_dono(a.dono)) == [a]
