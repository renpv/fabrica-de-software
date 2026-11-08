"""Regras de negócio das predefinições de fluxo. Views e API só chamam este módulo.

Este módulo não importa `projetos` (o contrato do `.importlinter` proíbe). Quem precisa
checar os projetos que usam uma predefinição se registra com `registrar_verificador_de_uso`
(o `projetos` faz isso no `ready()`); a contagem de usos vem da relação reversa `projetos`.
"""

import copy
import uuid
from collections.abc import Callable

from django.db import transaction
from django.db.models import ProtectedError

from apps.agentes.models import ContaAgente

from .metodos import METODOS
from .models import Predefinicao

ETAPAS = ["publicar_tasks", "implementar", "revisar", "merge", "promover"]
GATILHOS = ["anterior_concluida", "webhook", "temporizador", "decisao_humana"]

ROTULOS_ETAPAS = {
    "publicar_tasks": "Publicar as tasks",
    "implementar": "Implementar",
    "revisar": "Revisar",
    "merge": "Fazer o merge",
    "promover": "Promover para produção",
}
ROTULOS_GATILHOS = {
    "anterior_concluida": "Quando a etapa anterior terminar",
    "webhook": "Quando chegar um webhook",
    "temporizador": "Depois de um tempo",
    "decisao_humana": "Quando uma pessoa decidir",
}

TAMANHO_MAXIMO_MODELO = 64

# Função (predefinicao_ja_alterada) -> erros em pt-BR. Registradas por quem usa predefinições.
_verificadores_de_uso: list[Callable[[Predefinicao], list[str]]] = []


class ErroDePredefinicao(Exception):
    """Pedido recusado. A mensagem é pt-BR, diz o que fazer e não leva segredo."""


def registrar_verificador_de_uso(funcao: Callable[[Predefinicao], list[str]]) -> None:
    if funcao not in _verificadores_de_uso:
        _verificadores_de_uso.append(funcao)


def rotulos() -> dict:
    return {
        "etapas": [{"chave": c, "rotulo": ROTULOS_ETAPAS[c]} for c in ETAPAS],
        "gatilhos": [{"chave": c, "rotulo": ROTULOS_GATILHOS[c]} for c in GATILHOS],
        "metodos": [{"chave": m.chave, "rotulo": m.nome} for m in METODOS.values()],
    }


def _e_inteiro(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _validar_papel(dono, chave: str, papel) -> list[str]:
    if not isinstance(papel, dict):
        return [f"Etapa {chave}: o papel precisa ser um objeto com o campo tipo."]
    tipo = papel.get("tipo")
    if tipo not in ("conta", "humano", "central"):
        return [f"Etapa {chave}: o tipo do papel precisa ser conta, humano ou central."]
    if chave in ("implementar", "revisar") and tipo != "conta":
        return [f"Etapa {chave}: escolha uma conta de agente para esta etapa."]
    if chave == "promover" and tipo != "humano":
        return ["Etapa promover: só uma pessoa pode promover para produção (use o tipo humano)."]
    if chave in ("publicar_tasks", "merge") and tipo != "central":
        return [f"Etapa {chave}: esta etapa é feita pela central (use o tipo central)."]
    if tipo != "conta":
        return []
    erros = []
    modelo = papel.get("modelo")
    if modelo is not None and (not isinstance(modelo, str) or len(modelo) > TAMANHO_MAXIMO_MODELO):
        erros.append(
            f"Etapa {chave}: o modelo precisa ser um texto de até "
            f"{TAMANHO_MAXIMO_MODELO} caracteres."
        )
    bruto = papel.get("conta_id")
    try:
        if not isinstance(bruto, str):
            raise ValueError
        conta_id = uuid.UUID(bruto)
    except ValueError:
        erros.append(f"Etapa {chave}: escolha uma conta de agente da lista.")
        return erros
    if not ContaAgente.objects.filter(pk=conta_id, dono=dono).exists():
        erros.append(f"Etapa {chave}: conta não encontrada. Escolha uma das suas contas.")
    return erros


def validar_etapas(dono, etapas) -> list[str]:
    """Erros em pt-BR (lista vazia se estiver tudo certo). Nunca levanta por JSON malformado."""
    if not isinstance(etapas, list):
        return ["As etapas precisam ser uma lista."]
    erros: list[str] = []
    vistas: set[str] = set()
    for posicao, etapa in enumerate(etapas, start=1):
        if not isinstance(etapa, dict):
            erros.append(f"A etapa {posicao} precisa ser um objeto.")
            continue
        chave = etapa.get("chave")
        if not isinstance(chave, str) or chave not in ETAPAS:
            nome = chave if isinstance(chave, str) else "(vazia)"
            erros.append(f"Etapa desconhecida: {nome}. Use uma de: {', '.join(ETAPAS)}.")
            continue
        if chave in vistas:
            erros.append(f"Etapa repetida: {chave}. Cada etapa só pode aparecer uma vez.")
            continue
        vistas.add(chave)
        erros += _validar_papel(dono, chave, etapa.get("papel"))
        gatilho = etapa.get("gatilho")
        if not isinstance(gatilho, str) or gatilho not in GATILHOS:
            nome = gatilho if isinstance(gatilho, str) else "(vazio)"
            erros.append(
                f"Etapa {chave}: gatilho desconhecido: {nome}. Use um de: {', '.join(GATILHOS)}."
            )
        minutos = etapa.get("temporizador_minutos")
        if gatilho == "temporizador":
            if not _e_inteiro(minutos) or minutos < 1:
                erros.append(
                    f"Etapa {chave}: o gatilho temporizador exige temporizador_minutos, "
                    "um número inteiro de 1 em diante."
                )
        elif minutos is not None and (not _e_inteiro(minutos) or minutos < 1):
            erros.append(
                f"Etapa {chave}: temporizador_minutos precisa ser um número inteiro de 1 em diante."
            )
    return erros


def validar_predefinicao(dono, metodo, etapas) -> list[str]:
    erros = []
    if not isinstance(metodo, str) or metodo not in METODOS:
        erros.append(f"Método desconhecido: {metodo if isinstance(metodo, str) else ''}.")
    return erros + validar_etapas(dono, etapas)


def _recusar_se(erros: list[str]) -> None:
    if erros:
        raise ErroDePredefinicao(" ".join(erros))


def contas_da_predefinicao(predefinicao: Predefinicao) -> list[ContaAgente]:
    """As contas citadas nas etapas, sem repetir. Ignora o que não for um id válido."""
    ids: set[uuid.UUID] = set()
    etapas = predefinicao.etapas if isinstance(predefinicao.etapas, list) else []
    for etapa in etapas:
        papel = etapa.get("papel") if isinstance(etapa, dict) else None
        if isinstance(papel, dict) and papel.get("tipo") == "conta":
            try:
                ids.add(uuid.UUID(str(papel.get("conta_id"))))
            except ValueError:
                continue
    return list(ContaAgente.objects.filter(pk__in=ids, dono_id=predefinicao.dono_id))


def criar_predefinicao(dono, *, nome, descricao="", metodo="superpowers", etapas, **extra):
    _recusar_se(validar_predefinicao(dono, metodo, etapas))
    return Predefinicao.objects.create(
        dono=dono, nome=nome, descricao=descricao, metodo=metodo, etapas=etapas, **extra
    )


def atualizar_predefinicao(predefinicao: Predefinicao, dados: dict) -> Predefinicao:
    """Grava as mudanças e confere os projetos que usam a predefinição, tudo ou nada."""
    if "etapas" in dados or "metodo" in dados:
        _recusar_se(
            validar_predefinicao(
                predefinicao.dono,
                dados.get("metodo", predefinicao.metodo),
                dados.get("etapas", predefinicao.etapas),
            )
        )
    with transaction.atomic():
        for campo, valor in dados.items():
            setattr(predefinicao, campo, valor)
        predefinicao.save()
        erros: list[str] = []
        for verificador in _verificadores_de_uso:
            erros += verificador(predefinicao)
        if erros:
            transaction.set_rollback(True)
    _recusar_se(erros)
    return predefinicao


def _conta_do_dono(dono, conta: ContaAgente) -> None:
    if conta.dono_id != dono.id:
        raise ErroDePredefinicao("Conta não encontrada. Escolha uma das suas contas.")


def _etapas_do_padrao(executor: ContaAgente, revisor: ContaAgente) -> list[dict]:
    auto = "anterior_concluida"
    return [
        {"chave": "publicar_tasks", "papel": {"tipo": "central"}, "gatilho": auto},
        {
            "chave": "implementar",
            "papel": {"tipo": "conta", "conta_id": str(executor.id)},
            "gatilho": auto,
        },
        {
            "chave": "revisar",
            "papel": {"tipo": "conta", "conta_id": str(revisor.id)},
            "gatilho": auto,
        },
        {"chave": "merge", "papel": {"tipo": "central"}, "gatilho": auto},
        {"chave": "promover", "papel": {"tipo": "humano"}, "gatilho": "decisao_humana"},
    ]


def criar_padrao(dono, executor: ContaAgente, revisor: ContaAgente) -> Predefinicao:
    """O «Padrão» da spec (4.3): uma conta implementa e outra revisa."""
    _conta_do_dono(dono, executor)
    _conta_do_dono(dono, revisor)
    return Predefinicao.objects.create(
        dono=dono,
        nome="Padrão",
        descricao="Publica as tasks, implementa, revisa, faz o merge e espera o ok para produção.",
        metodo="superpowers",
        etapas=_etapas_do_padrao(executor, revisor),
        merge_autonomo=True,
    )


def duplicar(predefinicao: Predefinicao, nome: str) -> Predefinicao:
    return Predefinicao.objects.create(
        dono=predefinicao.dono,
        nome=nome,
        descricao=predefinicao.descricao,
        metodo=predefinicao.metodo,
        etapas=copy.deepcopy(predefinicao.etapas),
        merge_autonomo=predefinicao.merge_autonomo,
    )


def contar_usos(predefinicao: Predefinicao) -> int:
    return predefinicao.projetos.count()


def excluir_predefinicao(predefinicao: Predefinicao) -> None:
    def recusa() -> ErroDePredefinicao:
        return ErroDePredefinicao(
            f"Esta predefinição é usada por {contar_usos(predefinicao)} projeto(s)."
        )

    if contar_usos(predefinicao):
        raise recusa()
    try:
        predefinicao.delete()
    except ProtectedError:  # corrida: um projeto passou a usá-la agora
        raise recusa() from None


__all__ = [
    "ETAPAS",
    "GATILHOS",
    "ErroDePredefinicao",
    "atualizar_predefinicao",
    "contar_usos",
    "contas_da_predefinicao",
    "criar_padrao",
    "criar_predefinicao",
    "duplicar",
    "excluir_predefinicao",
    "registrar_verificador_de_uso",
    "rotulos",
    "validar_etapas",
    "validar_predefinicao",
]
