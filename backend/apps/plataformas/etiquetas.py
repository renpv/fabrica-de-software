"""Etiquetas que a central mantém nos repositórios (spec 4.2). Em três famílias:
ação (`acao:`), agente (`agente:`) e estado/tipo."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Etiqueta:
    nome: str
    cor: str  # hex sem "#"
    descricao: str  # curta, em pt-BR


COR_AGENTE = "5319e7"

ETIQUETAS_FIXAS: list[Etiqueta] = [
    Etiqueta("acao:implementar", "1d76db", "A central pede que um agente implemente a tarefa"),
    Etiqueta("acao:revisar", "fbca04", "A central pede a revisão do que foi entregue"),
    Etiqueta("acao:corrigir", "d93f0b", "A revisão pediu correções ao agente"),
    Etiqueta("em-andamento", "0e8a16", "Um agente está trabalhando nesta tarefa"),
    Etiqueta("precisa-humano", "b60205", "Parado, esperando uma decisão de uma pessoa"),
    Etiqueta("tarefa", "c5def5", "Tarefa publicada pela central"),
    Etiqueta("melhoria", "bfdadc", "Backlog: nenhum agente pega sozinho"),
]


def etiquetas_de_agentes(nomes: list[str]) -> list[Etiqueta]:
    """Uma `agente:<nome>` por nome, sem repetir, em ordem alfabética."""
    return [
        Etiqueta(f"agente:{nome}", COR_AGENTE, f"Tarefa para o agente {nome}")
        for nome in sorted(set(nomes))
    ]
