"""Códigos de erro do fluxo de conexão com o GitHub.

Quando `retorno/` ou `instalado/` falham, o navegador é levado para
`FABRICA_URL_PUBLICA/plataformas?erro=<código>`. O código é sempre um destes (nunca texto
livre nem corpo de resposta do GitHub); a tela de plataformas mostra a mensagem correspondente.
"""

MENSAGENS_DE_ERRO: dict[str, str] = {
    "sem_login": "Sua sessão expirou. Entre de novo e conecte o GitHub outra vez.",
    "estado_invalido": (
        "O link de conexão com o GitHub é inválido, expirou ou já foi usado. "
        "Comece de novo pela tela de plataformas."
    ),
    "conversao_falhou": (
        "O GitHub não aceitou criar o App (o código vale 1 hora e uma vez só). "
        "Comece de novo e crie o App outra vez."
    ),
    "conversao_sem_registro": (
        "O App foi criado no GitHub, mas a central não conseguiu salvar a conexão. "
        "Apague o App em https://github.com/settings/apps e comece de novo."
    ),
    "instalacao_invalida": (
        "Essa instalação não pertence ao App desta conexão. "
        "Instale o App criado pela central e tente de novo."
    ),
    "github_fora_do_ar": (
        "Não consegui falar com o GitHub agora, ou ele limitou as chamadas. "
        "Tente de novo em alguns minutos."
    ),
}
