"""Registro dos adaptadores de plataforma, por tipo."""

from ..models import ConexaoPlataforma
from .base import AdaptadorPlataforma
from .github import GitHubAdaptador
from .gitlab import GitLabAdaptador

REGISTRO = {"github": GitHubAdaptador, "gitlab": GitLabAdaptador}


def obter_adaptador(conexao: ConexaoPlataforma) -> AdaptadorPlataforma:
    classe = REGISTRO.get(conexao.tipo)
    if classe is None:
        raise ValueError(f"Tipo de plataforma desconhecido: {conexao.tipo}")
    return classe(conexao)
