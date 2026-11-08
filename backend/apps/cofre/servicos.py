"""Cifra e decifra segredos com Fernet. A primeira chave cifra; todas decifram."""

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings

_INSTRUCAO = (
    "Defina FABRICA_CHAVES_COFRE. Gere uma chave com: "
    'uv run python -c "from cryptography.fernet import Fernet; '
    'print(Fernet.generate_key().decode())"'
)


class ChaveDoCofreAusente(Exception):
    """A configuração das chaves do cofre está vazia ou inválida."""


class SegredoIlegivel(Exception):
    """O valor guardado não pôde ser decifrado com as chaves atuais."""


def _chaves() -> tuple[str, ...]:
    return tuple(c.strip() for c in settings.FABRICA_CHAVES_COFRE if c and c.strip())


@lru_cache(maxsize=8)
def _montar(chaves: tuple[str, ...]) -> MultiFernet:
    return MultiFernet([Fernet(c) for c in chaves])


def verificar_configuracao() -> None:
    """Falha cedo, na inicialização, se não houver chave ou se alguma for inválida."""
    chaves = _chaves()
    if not chaves:
        raise ChaveDoCofreAusente(_INSTRUCAO)
    for posicao, chave in enumerate(chaves, start=1):
        try:
            Fernet(chave)
        except ValueError:
            # Nunca inclui a chave na mensagem.
            raise ChaveDoCofreAusente(
                f"A chave {posicao} de FABRICA_CHAVES_COFRE não é uma chave Fernet válida. "
                f"Substitua por uma gerada com: {_INSTRUCAO.split('com: ', 1)[1]}"
            ) from None


def cifrar(texto: str) -> str:
    verificar_configuracao()
    return _montar(_chaves()).encrypt(texto.encode()).decode()


def decifrar(token: str) -> str:
    verificar_configuracao()
    try:
        return _montar(_chaves()).decrypt(token.encode()).decode()
    except InvalidToken:
        raise SegredoIlegivel(
            "Não foi possível decifrar o segredo. A chave que o cifrou provavelmente "
            "saiu de FABRICA_CHAVES_COFRE: recoloque-a na lista (depois da chave nova) "
            "ou cadastre o segredo de novo."
        ) from None
