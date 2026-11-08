"""Métodos de desenvolvimento (superpowers, Spec Kit...). O comando de cada etapa é do Plano 3."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Metodo:
    chave: str
    nome: str
    pasta_specs: str
    pasta_planos: str


METODOS: dict[str, Metodo] = {
    "superpowers": Metodo(
        "superpowers", "superpowers", "docs/superpowers/specs", "docs/superpowers/plans"
    ),
}
