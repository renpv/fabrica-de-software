import pytest
from cryptography.fernet import Fernet
from django.db import connection
from django.test import override_settings

from apps.cofre import servicos
from apps.cofre.campos import ValorSecreto
from apps.cofre.servicos import ChaveDoCofreAusente, cifrar, decifrar
from tests.apoio.models import RegistroComSegredo


def test_ida_e_volta():
    assert decifrar(cifrar("abc")) == "abc"


def test_rotacao():
    antiga = Fernet.generate_key().decode()
    nova = Fernet.generate_key().decode()
    with override_settings(FABRICA_CHAVES_COFRE=[antiga]):
        token = cifrar("abc")
    with override_settings(FABRICA_CHAVES_COFRE=[nova, antiga]):
        assert decifrar(token) == "abc"
        # O que se cifra agora usa a chave nova: a antiga já pode sair.
        novo_token = cifrar("abc")
    with override_settings(FABRICA_CHAVES_COFRE=[nova]):
        assert decifrar(novo_token) == "abc"


def test_token_de_chave_removida_explica_o_que_fazer():
    outra = Fernet.generate_key().decode()
    token = cifrar("segredo-xyz")
    with override_settings(FABRICA_CHAVES_COFRE=[outra]):
        with pytest.raises(servicos.SegredoIlegivel) as erro:
            decifrar(token)
    assert "FABRICA_CHAVES_COFRE" in str(erro.value)
    assert token not in str(erro.value)
    assert "segredo-xyz" not in str(erro.value)


def test_sem_chave_falha_com_instrucao():
    esperado = (
        "Defina FABRICA_CHAVES_COFRE. Gere uma chave com: "
        'uv run python -c "from cryptography.fernet import Fernet; '
        'print(Fernet.generate_key().decode())"'
    )
    with override_settings(FABRICA_CHAVES_COFRE=[]):
        with pytest.raises(ChaveDoCofreAusente) as erro:
            servicos.verificar_configuracao()
    assert str(erro.value) == esperado


def test_chave_invalida_falha_sem_mostrar_a_chave():
    with override_settings(FABRICA_CHAVES_COFRE=["isto-nao-e-uma-chave"]):
        with pytest.raises(ChaveDoCofreAusente) as erro:
            servicos.verificar_configuracao()
    assert "isto-nao-e-uma-chave" not in str(erro.value)
    assert "FABRICA_CHAVES_COFRE" in str(erro.value)


@pytest.mark.django_db
def test_banco_guarda_cifrado():
    obj = RegistroComSegredo.objects.create(credenciais={"chave": "abc-texto-puro"})
    with connection.cursor() as cursor:
        cursor.execute("SELECT credenciais FROM apoio_registrocomsegredo WHERE id = %s", [obj.pk])
        bruto = cursor.fetchone()[0]
    assert "abc-texto-puro" not in bruto
    assert RegistroComSegredo.objects.get(pk=obj.pk).credenciais == {"chave": "abc-texto-puro"}


def test_repr_nao_vaza_antes_de_salvar():
    obj = RegistroComSegredo(credenciais={"a": "abc"})
    assert isinstance(obj.credenciais, ValorSecreto)
    assert "abc" not in repr(obj.credenciais)
    obj.credenciais = {"a": "xyz"}
    assert "xyz" not in repr(obj.credenciais) and obj.credenciais["a"] == "xyz"
    obj.credenciais = None
    assert obj.credenciais is None


@pytest.mark.django_db
def test_repr_nao_vaza():
    RegistroComSegredo.objects.create(credenciais={"chave": "abc"})
    obj = RegistroComSegredo.objects.get()
    assert isinstance(obj.credenciais, ValorSecreto)
    assert "abc" not in repr(obj.credenciais)
    assert "abc" not in str(obj.credenciais)
    assert repr(obj.credenciais) == "<segredo>"
    assert obj.credenciais["chave"] == "abc"


@pytest.mark.django_db
def test_nulo_continua_nulo():
    obj = RegistroComSegredo.objects.create(credenciais=None)
    assert RegistroComSegredo.objects.get(pk=obj.pk).credenciais is None
