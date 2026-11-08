"""Contrato de um provedor de agente (Strategy): um provedor por tipo de agente."""

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class ResultadoTeste:
    ok: bool
    status: Literal["ok", "falha", "aguardando_runner"]
    mensagem: str  # pt-BR, pronta para mostrar


@dataclass(frozen=True)
class CampoCadastro:
    chave: str
    rotulo: str
    secreto: bool
    ajuda: str
    obrigatorio: bool = True


@dataclass(frozen=True)
class PassoGuia:
    texto: str
    link: str | None = None


class ProvedorDeAgente(Protocol):
    tipo: str
    nome: str
    etiqueta: str  # nome do agente na etiqueta `agente:<etiqueta>`
    modelos_sugeridos: list[str]
    campos: list[CampoCadastro]
    guia: list[PassoGuia]

    def testar(self, credenciais: dict[str, str], config: dict) -> ResultadoTeste: ...
