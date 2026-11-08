import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from apps.donos.models import Dono
from apps.plataformas.models import ConexaoPlataforma


@pytest.fixture(scope="session")
def chaves_rsa():
    """Par RSA só para os testes: (pem privado, pem público)."""
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = privada.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    publica = (
        privada.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    return pem, publica


@pytest.fixture
def conexao_github(db, chaves_rsa):
    """Conexão GitHub já instalada (installation_id 777)."""
    dono = Dono.objects.create(nome="Dono do GitHub")
    return ConexaoPlataforma.objects.create(
        dono=dono,
        nome="Meu GitHub",
        tipo="github",
        credenciais={
            "app_id": "123",
            "slug": "fabrica-teste",
            "pem": chaves_rsa[0],
            "webhook_secret": "wh-secreto-xyz",
            "client_id": "Iv1.abc",
            "client_secret": "cs-secreto-xyz",
        },
        config={"installation_id": "777"},
    )
