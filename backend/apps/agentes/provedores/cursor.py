"""Provedor do Cursor (Cloud Agents API v1). A chave é testada em GET /v1/me."""

import httpx

from .base import CampoCadastro, PassoGuia, ResultadoTeste

URL_ME = "https://api.cursor.com/v1/me"
TIMEOUT_SEGUNDOS = 10


class ProvedorCursor:
    tipo = "cursor"
    nome = "Cursor"
    etiqueta = "cursor"
    modelos_sugeridos: list[str] = []  # a lista vem da API (GET /v1/models) depois
    campos = [
        CampoCadastro(
            chave="api_key",
            rotulo="Chave de API do Cursor",
            secreto=True,
            ajuda="Cole a chave criada no painel do Cursor.",
        )
    ]
    guia = [
        PassoGuia(
            texto="Abra o painel do Cursor, em Dashboard > API Keys, e crie uma chave.",
            link="https://cursor.com/dashboard/api",
        ),
        PassoGuia(texto="Dê um nome à chave (por exemplo, Fábrica de software) e copie o valor."),
        PassoGuia(texto="Cole a chave aqui e clique em testar."),
        PassoGuia(
            texto="Dúvidas sobre a chave? Veja a documentação da API do Cursor.",
            link="https://cursor.com/docs/api",
        ),
    ]

    def testar(self, credenciais: dict[str, str], config: dict) -> ResultadoTeste:
        chave = credenciais.get("api_key", "")
        if not chave:
            return ResultadoTeste(
                ok=False, status="falha", mensagem="Cole a chave de API do Cursor para testar."
            )
        try:
            resposta = httpx.get(
                URL_ME,
                headers={"Authorization": f"Bearer {chave}"},
                timeout=TIMEOUT_SEGUNDOS,
            )
        except UnicodeEncodeError:
            return ResultadoTeste(
                ok=False,
                status="falha",
                mensagem=(
                    "A chave tem caracteres inválidos (acentos ou aspas). "
                    "Cole só a chave, sem aspas."
                ),
            )
        except httpx.TransportError:
            return ResultadoTeste(
                ok=False,
                status="falha",
                mensagem="Não consegui falar com o Cursor agora. Tente de novo em instantes.",
            )
        if resposta.status_code in (401, 403):
            return ResultadoTeste(
                ok=False,
                status="falha",
                mensagem=(
                    "A chave foi recusada pelo Cursor. "
                    "Gere uma nova no painel do Cursor e cole aqui."
                ),
            )
        if resposta.status_code != 200:
            return ResultadoTeste(
                ok=False,
                status="falha",
                mensagem=(
                    f"O Cursor respondeu com erro (HTTP {resposta.status_code}). "
                    "Tente de novo em instantes."
                ),
            )
        try:
            dados = resposta.json()
        except ValueError:
            dados = {}
        quem = (
            (dados.get("userEmail") or dados.get("apiKeyName")) if isinstance(dados, dict) else None
        )
        return ResultadoTeste(
            ok=True, status="ok", mensagem=f"Conectado como {quem or 'o Cursor'}."
        )
