"""Regras de negócio das contas de agente. Views e API só chamam este módulo."""

from dataclasses import asdict

from django.utils import timezone

from .models import ContaAgente
from .provedores import REGISTRO, ResultadoTeste, obter_provedor


def limpar_credenciais(tipo: str, dados: dict[str, str]) -> dict[str, str]:
    """Tira espaços e quebras de linha das pontas de cada valor (as internas ficam: chave PEM)."""
    obter_provedor(tipo)  # valida o tipo
    return {chave: valor.strip() for chave, valor in dados.items()}


def testar_dados(tipo: str, credenciais: dict[str, str], config: dict) -> ResultadoTeste:
    """Testa as credenciais sem salvar nada."""
    provedor = obter_provedor(tipo)
    return provedor.testar(limpar_credenciais(tipo, credenciais), config)


def testar_conta(conta) -> ResultadoTeste:
    """Testa a conta e grava o resultado nela."""
    resultado = testar_dados(conta.tipo, conta.credenciais, conta.config)
    conta.status = resultado.status
    conta.ultimo_teste_em = timezone.now()
    limite = conta._meta.get_field("ultimo_teste_mensagem").max_length
    conta.ultimo_teste_mensagem = resultado.mensagem[:limite]
    conta.save(
        update_fields=["status", "ultimo_teste_em", "ultimo_teste_mensagem", "atualizado_em"]
    )
    return resultado


def listar_tipos() -> list[dict]:
    """Os tipos de agente que a central conhece, em ordem alfabética, prontos para a API."""
    return [
        {
            "tipo": p.tipo,
            "nome": p.nome,
            "etiqueta": p.etiqueta,
            "modelos_sugeridos": list(p.modelos_sugeridos),
            "campos": [asdict(c) for c in p.campos],
            "guia": [asdict(g) for g in p.guia],
        }
        for _, p in sorted(REGISTRO.items())
    ]


def validar_credenciais(tipo: str, dados: object, *, exigir_obrigatorias: bool) -> dict[str, str]:
    """Confere o formato das credenciais e devolve o dict limpo. ValueError em pt-BR.

    As mensagens citam o nome do campo, nunca o valor.
    """
    provedor = obter_provedor(tipo)
    if not isinstance(dados, dict) or not all(
        isinstance(c, str) and isinstance(v, str) for c, v in dados.items()
    ):
        raise ValueError("Envie as credenciais como um objeto de textos, um por campo.")
    conhecidas = {c.chave for c in provedor.campos}
    desconhecidas = sorted(set(dados) - conhecidas)
    if desconhecidas:
        raise ValueError(
            f"Campo de credencial desconhecido para {provedor.nome}: "
            f"{', '.join(desconhecidas)}. Remova-o e tente de novo."
        )
    limpas = limpar_credenciais(tipo, dados)
    if exigir_obrigatorias:
        for campo in provedor.campos:
            if campo.secreto and campo.obrigatorio and not limpas.get(campo.chave):
                raise ValueError(f"Preencha o campo «{campo.rotulo}».")
    return limpas


def criar_conta(dono, dados: dict) -> ContaAgente:
    """Cria a conta do dono, limpando as pontas das credenciais antes de gravar."""
    dados = dict(dados)
    tipo = dados["tipo"]
    dados["credenciais"] = limpar_credenciais(tipo, dados.get("credenciais") or {})
    return ContaAgente.objects.create(dono=dono, **dados)


def atualizar_conta(conta: ContaAgente, dados: dict) -> ContaAgente:
    """Atualiza a conta. Credenciais novas substituem as antigas e zeram o status."""
    dados = dict(dados)
    dados.pop("tipo", None)  # o tipo não muda depois de criada
    if "credenciais" in dados:
        dados["credenciais"] = limpar_credenciais(conta.tipo, dados["credenciais"])
        conta.status = ContaAgente.Status.NAO_TESTADA
    for campo, valor in dados.items():
        setattr(conta, campo, valor)
    conta.save()
    return conta


def excluir_conta(conta: ContaAgente) -> None:
    conta.delete()
