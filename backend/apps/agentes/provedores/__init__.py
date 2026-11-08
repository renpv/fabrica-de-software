"""Registro dos provedores de agente, por tipo."""

from .base import CampoCadastro, PassoGuia, ProvedorDeAgente, ResultadoTeste
from .claude_local import ProvedorClaudeLocal
from .cursor import ProvedorCursor

REGISTRO: dict[str, ProvedorDeAgente] = {
    p.tipo: p for p in (ProvedorCursor(), ProvedorClaudeLocal())
}


def obter_provedor(tipo: str) -> ProvedorDeAgente:
    try:
        return REGISTRO[tipo]
    except KeyError:
        raise ValueError(f"Tipo de agente desconhecido: {tipo}") from None


__all__ = [
    "REGISTRO",
    "CampoCadastro",
    "PassoGuia",
    "ProvedorDeAgente",
    "ResultadoTeste",
    "obter_provedor",
]
