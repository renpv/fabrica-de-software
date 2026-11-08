"""Regras de negócio dos projetos. Views e API só chamam este módulo.

Fala com plataformas e agentes só pelas interfaces públicas deles (`obter_adaptador`,
`url_webhook`, `ETIQUETAS_FIXAS`, `REGISTRO` de provedores).
"""

import re
from dataclasses import asdict

from django.db import transaction
from django.utils import timezone

from apps.agentes.provedores import REGISTRO as PROVEDORES
from apps.plataformas import servicos as plataformas
from apps.plataformas.adaptadores import obter_adaptador
from apps.plataformas.adaptadores.base import ErroDePlataforma, ItemConferencia, Repositorio
from apps.plataformas.etiquetas import ETIQUETAS_FIXAS, Etiqueta, etiquetas_de_agentes

from .models import Projeto

# `dono/repo` no GitHub; no GitLab pode haver grupos aninhados (`a/b/c`).
CAMINHO_VALIDO = re.compile(r"^[\w.-]+(/[\w.-]+)+$")


class ErroDeProjeto(Exception):
    """Pedido recusado. A mensagem é pt-BR, diz o que fazer e não leva segredo."""


def etiquetas_do_projeto() -> list[Etiqueta]:
    return [*ETIQUETAS_FIXAS, *etiquetas_de_agentes([p.etiqueta for p in PROVEDORES.values()])]


def url_webhook(projeto: Projeto) -> str:
    return plataformas.url_webhook(projeto.conexao)


def _repo_do_projeto(projeto: Projeto) -> Repositorio:
    if not CAMINHO_VALIDO.fullmatch(projeto.repositorio_caminho):
        raise ErroDeProjeto(
            "O caminho do repositório gravado é inválido. Apague o projeto e cadastre de novo."
        )
    return Repositorio(
        projeto.repositorio_id_externo, projeto.repositorio_caminho, projeto.repositorio_url
    )


def _gravar(projeto: Projeto, itens: list[ItemConferencia]) -> list[ItemConferencia]:
    projeto.ultima_conferencia = [asdict(i) for i in itens]
    projeto.ultima_conferencia_em = timezone.now()
    projeto.save(update_fields=["ultima_conferencia", "ultima_conferencia_em", "atualizado_em"])
    return itens


def conferir_projeto(projeto: Projeto) -> list[ItemConferencia]:
    """Confere o repositório sem alterar nada. Levanta ErroDePlataforma (pt-BR)."""
    adaptador = obter_adaptador(projeto.conexao)
    itens = adaptador.conferir(
        _repo_do_projeto(projeto), url_webhook(projeto), etiquetas_do_projeto()
    )
    return _gravar(projeto, itens)


def preparar_projeto(projeto: Projeto) -> list[ItemConferencia]:
    """Cria o que falta no repositório (etiquetas, webhook). Idempotente."""
    adaptador = obter_adaptador(projeto.conexao)
    itens = adaptador.preparar(
        _repo_do_projeto(projeto), url_webhook(projeto), etiquetas_do_projeto()
    )
    return _gravar(projeto, itens)


def criar_projeto(dono, *, nome, conexao, repositorio_id_externo, cliente=None) -> Projeto:
    """Busca o repositório na listagem da plataforma, grava o projeto e já o prepara.

    A busca e a gravação são uma transação só. Se o `preparar` falhar depois, o projeto fica
    gravado (a pessoa tenta de novo em «Preparar») e a mensagem vai em `erro_ao_preparar`.
    Levanta ErroDeProjeto (pedido recusado) ou ErroDePlataforma (listagem falhou).
    """
    if conexao.dono_id != dono.id or (cliente is not None and cliente.dono_id != dono.id):
        raise ErroDeProjeto("Conexão ou cliente não encontrado. Escolha um dos seus.")
    with transaction.atomic():
        repo = next(
            (r for r in obter_adaptador(conexao).listar_repositorios()
             if r.id_externo == repositorio_id_externo),
            None,
        )  # fmt: skip
        if repo is None:
            raise ErroDeProjeto(
                "Esse repositório não está acessível por esta conexão. "
                "Confira o acesso do token ou do App e tente de novo."
            )
        if not CAMINHO_VALIDO.fullmatch(repo.caminho):
            raise ErroDeProjeto(
                "A plataforma devolveu um caminho de repositório inesperado. "
                "Tente de novo ou escolha outro repositório."
            )
        if Projeto.objects.filter(
            dono=dono, conexao=conexao, repositorio_id_externo=repo.id_externo
        ).exists():
            raise ErroDeProjeto("Esse repositório já está cadastrado como projeto.")
        projeto = Projeto.objects.create(
            dono=dono,
            nome=nome,
            conexao=conexao,
            repositorio_caminho=repo.caminho,
            repositorio_id_externo=repo.id_externo,
            repositorio_url=repo.url_web,
            cliente=cliente,
        )
    try:
        preparar_projeto(projeto)
    except ErroDePlataforma as erro:
        projeto.erro_ao_preparar = str(erro)
    return projeto


def excluir_projeto(projeto: Projeto) -> None:
    projeto.delete()


__all__ = [
    "ErroDePlataforma",
    "ErroDeProjeto",
    "conferir_projeto",
    "criar_projeto",
    "etiquetas_do_projeto",
    "excluir_projeto",
    "preparar_projeto",
    "url_webhook",
]
