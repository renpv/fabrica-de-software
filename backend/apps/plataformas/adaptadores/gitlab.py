"""Adaptador do GitLab (instância self-hosted) por token de acesso pessoal ou de projeto/grupo.

O token vai só no cabeçalho `PRIVATE-TOKEN`, sempre para a URL da própria conexão. Nenhum
segredo, token nem corpo de resposta do GitLab entra em log ou em mensagem de erro, e as
chamadas não seguem redirecionamentos (o token não sai da instância).
"""

import httpx

from ..etiquetas import Etiqueta
from .base import ErroDePlataforma, ItemConferencia, Repositorio, ResultadoTeste

TIMEOUT_SEGUNDOS = 10
POR_PAGINA = 100
MAX_PAGINAS = 100  # trava de segurança contra paginação sem fim
NIVEL_MAINTAINER = 40  # é preciso ser Maintainer para criar o webhook

COD_FORA_DO_AR = "gitlab_fora_do_ar"
COD_TOKEN = "gitlab_token_invalido"

MSG_SEM_API = "O token precisa do escopo api. Crie outro marcando api."
MSG_RECUSADO = "O GitLab recusou o token. Confira se ele não expirou."
MSG_TOKEN_INVALIDO = (
    "O token tem caracteres inválidos (acentos, espaços ou quebras de linha). Cole só o token."
)
MSG_INESPERADA = "O GitLab devolveu uma resposta inesperada. Tente de novo."


def token_valido(token) -> bool:
    return (
        isinstance(token, str)
        and bool(token)
        and token.isascii()
        and token.isprintable()
        and " " not in token
    )


def erro_de_status(resposta) -> ErroDePlataforma:
    """Traduz um status HTTP inesperado em mensagem pt-BR (sem o corpo da resposta)."""
    if resposta.status_code == 429:
        return ErroDePlataforma(
            "O GitLab limitou as chamadas por enquanto. Tente de novo em alguns minutos.",
            COD_FORA_DO_AR,
        )
    if resposta.status_code == 401:
        return ErroDePlataforma(MSG_RECUSADO, COD_TOKEN)
    if resposta.status_code == 403:
        return ErroDePlataforma(
            "O GitLab negou o acesso. O token precisa ser Maintainer (ou mais) no projeto.",
            COD_TOKEN,
        )
    return ErroDePlataforma(
        f"O GitLab respondeu com erro (HTTP {resposta.status_code}). Tente de novo em instantes.",
        COD_FORA_DO_AR,
    )


def _inesperada() -> ErroDePlataforma:
    return ErroDePlataforma(MSG_INESPERADA, COD_FORA_DO_AR)


class GitLabAdaptador:
    def __init__(self, conexao):
        credenciais = dict(conexao.credenciais or {})
        self._url = str(conexao.url_base or "").rstrip("/")
        self._token = credenciais.get("token")
        self._segredo_webhook = str(credenciais.get("webhook_secret") or "")

    # --- HTTP ---------------------------------------------------------------------------

    def _requisitar(self, metodo: str, caminho: str, **opcoes):
        if not token_valido(self._token):
            raise ErroDePlataforma(MSG_TOKEN_INVALIDO, COD_TOKEN)
        try:
            return httpx.request(
                metodo,
                f"{self._url}/api/v4{caminho}",
                headers={"PRIVATE-TOKEN": self._token},
                timeout=TIMEOUT_SEGUNDOS,
                follow_redirects=False,
                **opcoes,
            )
        except httpx.TransportError:
            raise ErroDePlataforma(
                f"Não consegui acessar {self._url}. "
                "Confira o endereço e se a central alcança a rede da instância.",
                COD_FORA_DO_AR,
            ) from None

    def _paginas(self, caminho: str, params: dict | None = None):
        """Percorre todas as páginas (`X-Next-Page`). Nunca trunca em silêncio."""
        params = {**(params or {}), "per_page": POR_PAGINA}
        pagina = ""
        for _ in range(MAX_PAGINAS):
            consulta = {**params, **({"page": pagina} if pagina else {})}
            resposta = self._requisitar("GET", caminho, params=consulta)
            if resposta.status_code != 200:
                raise erro_de_status(resposta)
            try:
                dados = resposta.json()
            except ValueError:
                raise _inesperada() from None
            if not isinstance(dados, list):
                raise _inesperada()
            yield dados
            pagina = resposta.headers.get("x-next-page", "").strip()
            if not pagina.isdigit():
                return
        raise ErroDePlataforma(
            "A lista do GitLab é grande demais para a central carregar inteira "
            f"(mais de {MAX_PAGINAS * POR_PAGINA} itens).",
            COD_FORA_DO_AR,
        )

    # --- contrato AdaptadorPlataforma ---------------------------------------------------

    def testar(self) -> ResultadoTeste:
        try:
            resposta = self._requisitar("GET", "/personal_access_tokens/self")
            if resposta.status_code != 200:
                raise erro_de_status(resposta)
            try:
                escopos = resposta.json().get("scopes")
            except ValueError, AttributeError:
                raise _inesperada() from None
        except ErroDePlataforma as erro:
            return ResultadoTeste(ok=False, status="falha", mensagem=str(erro))
        if not isinstance(escopos, list) or "api" not in escopos:
            return ResultadoTeste(ok=False, status="falha", mensagem=MSG_SEM_API)
        return ResultadoTeste(ok=True, status="ok", mensagem=f"Conectado ao GitLab em {self._url}.")

    def listar_repositorios(self) -> list[Repositorio]:
        params = {"membership": "true", "min_access_level": NIVEL_MAINTAINER}
        repositorios: list[Repositorio] = []
        for pagina in self._paginas("/projects", params):
            try:
                repositorios += [
                    Repositorio(str(p["id"]), p["path_with_namespace"], p["web_url"])
                    for p in pagina
                ]
            except KeyError, TypeError:
                raise _inesperada() from None
        return repositorios

    def conferir(
        self, repo: Repositorio, url_webhook: str, etiquetas: list[Etiqueta]
    ) -> list[ItemConferencia]:
        faltando = self._etiquetas_faltando(repo, etiquetas)
        return [
            self._item_etiquetas(faltando),
            self._item_webhook(self._tem_webhook(repo, url_webhook)),
        ]

    def preparar(
        self, repo: Repositorio, url_webhook: str, etiquetas: list[Etiqueta]
    ) -> list[ItemConferencia]:
        faltando = self._etiquetas_faltando(repo, etiquetas)
        sobraram = self._criar_etiquetas(repo, faltando)
        existe = self._tem_webhook(repo, url_webhook)
        if not existe:
            existe = self._criar_webhook(repo, url_webhook)
        return [self._item_etiquetas(sobraram), self._item_webhook(existe)]

    # --- etiquetas ----------------------------------------------------------------------

    def _etiquetas_faltando(self, repo: Repositorio, etiquetas: list[Etiqueta]) -> list[Etiqueta]:
        existentes: set[str] = set()
        for pagina in self._paginas(f"/projects/{repo.id_externo}/labels"):
            try:
                existentes |= {e["name"].lower() for e in pagina}
            except KeyError, TypeError, AttributeError:
                raise _inesperada() from None
        return [e for e in etiquetas if e.nome.lower() not in existentes]

    def _criar_etiquetas(self, repo: Repositorio, faltando: list[Etiqueta]) -> list[Etiqueta]:
        """Cria as etiquetas. 409 (já existe) conta como ok. Devolve as que não deram."""
        sobraram = []
        for etiqueta in faltando:
            resposta = self._requisitar(
                "POST",
                f"/projects/{repo.id_externo}/labels",
                json={
                    "name": etiqueta.nome,
                    "color": f"#{etiqueta.cor}",
                    "description": etiqueta.descricao,
                },
            )
            if resposta.status_code not in (201, 409):
                sobraram.append(etiqueta)
        return sobraram

    @staticmethod
    def _item_etiquetas(faltando: list[Etiqueta]) -> ItemConferencia:
        if not faltando:
            return ItemConferencia(
                "etiquetas", "Etiquetas", True, "Todas as etiquetas existem.", True
            )
        nomes = ", ".join(e.nome for e in faltando)
        return ItemConferencia(
            "etiquetas", "Etiquetas", False, f"Faltam as etiquetas: {nomes}. Use «Preparar».", True
        )

    # --- webhook ------------------------------------------------------------------------

    def _tem_webhook(self, repo: Repositorio, url_webhook: str) -> bool:
        for pagina in self._paginas(f"/projects/{repo.id_externo}/hooks"):
            try:
                if any(h["url"] == url_webhook for h in pagina):
                    return True
            except KeyError, TypeError:
                raise _inesperada() from None
        return False

    def _criar_webhook(self, repo: Repositorio, url_webhook: str) -> bool:
        resposta = self._requisitar(
            "POST",
            f"/projects/{repo.id_externo}/hooks",
            json={
                "url": url_webhook,
                "token": self._segredo_webhook,
                "issues_events": True,
                "merge_requests_events": True,
                "note_events": True,
                "pipeline_events": True,
                "enable_ssl_verification": True,
            },
        )
        return resposta.status_code == 201

    @staticmethod
    def _item_webhook(existe: bool) -> ItemConferencia:
        if existe:
            return ItemConferencia("webhook", "Webhook", True, "Webhook configurado.", True)
        return ItemConferencia(
            "webhook",
            "Webhook",
            False,
            "O projeto não tem o webhook da central (ou o token não é Maintainer). Use «Preparar».",
            True,
        )
