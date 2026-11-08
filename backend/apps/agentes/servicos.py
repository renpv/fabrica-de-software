"""Regras de negócio das contas de agente. Views e API só chamam este módulo."""

from django.utils import timezone

from .provedores import ResultadoTeste, obter_provedor


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
    conta.ultimo_teste_mensagem = resultado.mensagem
    conta.save(
        update_fields=["status", "ultimo_teste_em", "ultimo_teste_mensagem", "atualizado_em"]
    )
    return resultado
