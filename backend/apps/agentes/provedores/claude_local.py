"""Provedor do Claude no PC do usuário. Sem segredo: vale o login do `claude` já feito lá."""

from .base import PassoGuia, ResultadoTeste


class ProvedorClaudeLocal:
    tipo = "claude_local"
    nome = "Claude (no seu PC)"
    etiqueta = "claude"
    modelos_sugeridos = ["opus", "sonnet", "haiku"]
    campos: list = []
    guia = [
        PassoGuia(
            texto="No seu PC, abra o terminal e faça o login do Claude Code "
            "com o comando `claude`. "
            "A central não guarda a sua senha: usa o login que já está feito na máquina."
        ),
        PassoGuia(texto="Instale e inicie o runner da fábrica no mesmo PC."),
        PassoGuia(texto="Quando o runner se conectar, esta conta fica pronta."),
    ]

    def testar(self, credenciais: dict[str, str], config: dict) -> ResultadoTeste:
        return ResultadoTeste(
            ok=False,
            status="aguardando_runner",
            mensagem="Esta conta fica pronta quando o runner do seu PC se conectar.",
        )
