"""Contrato de uma plataforma de código (Adapter): um adaptador por tipo de plataforma."""

from dataclasses import dataclass
from typing import Literal, Protocol

from ..etiquetas import Etiqueta


class ErroDePlataforma(Exception):
    """Falha ao falar com a plataforma. A mensagem é pt-BR, pronta para mostrar, e nunca
    leva segredo nem o corpo da resposta da plataforma.

    `codigo` é um dos códigos de `erros.MENSAGENS_DE_ERRO`, usado nos redirecionamentos."""

    def __init__(self, mensagem: str, codigo: str = "github_fora_do_ar"):
        super().__init__(mensagem)
        self.codigo = codigo


@dataclass(frozen=True)
class ResultadoTeste:
    ok: bool
    status: Literal["ok", "falha"]
    mensagem: str  # pt-BR, pronta para mostrar


@dataclass(frozen=True)
class Repositorio:
    id_externo: str
    caminho: str  # "dono/repo" ou "grupo/sub/projeto"
    url_web: str


@dataclass(frozen=True)
class ItemConferencia:
    chave: str
    titulo: str
    ok: bool
    mensagem: str
    consertavel: bool


class AdaptadorPlataforma(Protocol):
    def testar(self) -> ResultadoTeste: ...

    def listar_repositorios(self) -> list[Repositorio]: ...  # todas as páginas

    def conferir(
        self, repo: Repositorio, url_webhook: str, etiquetas: list[Etiqueta]
    ) -> list[ItemConferencia]: ...

    def preparar(  # idempotente
        self, repo: Repositorio, url_webhook: str, etiquetas: list[Etiqueta]
    ) -> list[ItemConferencia]: ...
