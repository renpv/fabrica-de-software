"""Adaptador do GitHub, por GitHub App criado pela central (manifest flow).

Autenticação: JWT RS256 do App para as rotas `/app/*` e token de instalação (curta duração)
para as rotas do repositório. Nenhum segredo, token nem corpo de resposta do GitHub entra
em log ou em mensagem de erro.
"""

import re
import time
from urllib.parse import urlparse

import httpx
import jwt

from ..etiquetas import Etiqueta
from .base import ErroDePlataforma, ItemConferencia, Repositorio, ResultadoTeste

API = "https://api.github.com"
VERSAO_API = "2026-03-10"
TIMEOUT_SEGUNDOS = 10
POR_PAGINA = 100
MAX_PAGINAS = 100  # trava de segurança contra paginação sem fim
SLUG_VALIDO = re.compile(r"^[a-z0-9-]+$")

MSG_REDE = "Não consegui falar com o GitHub agora. Tente de novo em instantes."
MSG_CHAVE = "A chave privada do App do GitHub está inválida. Remova esta conexão e crie-a de novo."
MSG_RECUSADO = "O GitHub recusou as credenciais do App. Remova esta conexão e crie-a de novo."


def link_de_instalacao(slug: str) -> str:
    return f"https://github.com/apps/{slug}/installations/new"


def _cabecalhos(autorizacao: str | None = None) -> dict[str, str]:
    cabecalhos = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": VERSAO_API}
    if autorizacao:
        cabecalhos["Authorization"] = f"Bearer {autorizacao}"
    return cabecalhos


def _requisitar(metodo: str, url: str, autorizacao: str | None = None, **opcoes):
    try:
        return httpx.request(
            metodo, url, headers=_cabecalhos(autorizacao), timeout=TIMEOUT_SEGUNDOS, **opcoes
        )
    except httpx.TransportError:
        raise ErroDePlataforma(MSG_REDE) from None


def converter_manifesto(codigo: str) -> dict[str, str]:
    """Troca o `code` do manifest flow pelas credenciais do App (uso único, sem nova tentativa).

    Devolve as credenciais já validadas e limpas. A resposta do GitHub carrega a chave privada,
    então nada dela vai para mensagem de erro.
    """
    resposta = _requisitar("POST", f"{API}/app-manifests/{codigo}/conversions")
    if resposta.status_code in (404, 422):
        raise ErroDePlataforma(
            "O GitHub não aceitou o código de criação do App (ele expira em 1 hora e vale uma "
            "vez só). Comece de novo e crie o App outra vez."
        )
    if resposta.status_code not in (200, 201):
        raise ErroDePlataforma(
            f"O GitHub respondeu com erro (HTTP {resposta.status_code}) ao criar o App. "
            "Tente de novo em instantes."
        )
    inesperada = ErroDePlataforma(
        "O GitHub devolveu uma resposta inesperada ao criar o App. Comece de novo."
    )
    try:
        dados = resposta.json()
    except ValueError:
        raise inesperada from None
    if not isinstance(dados, dict):
        raise inesperada
    textos = {}
    for campo in ("slug", "pem", "webhook_secret", "client_id", "client_secret"):
        valor = dados.get(campo)
        if not isinstance(valor, str) or not valor.strip():
            raise inesperada
        textos[campo] = valor.strip()  # só as pontas: o PEM mantém as quebras internas
    app_id = dados.get("id")
    if isinstance(app_id, bool) or not isinstance(app_id, int | str) or not str(app_id).strip():
        raise inesperada
    if not SLUG_VALIDO.fullmatch(textos["slug"]):
        raise inesperada
    return {"app_id": str(app_id).strip(), **textos}


def montar_manifesto(nome: str, url_publica: str) -> dict:
    base = url_publica.rstrip("/")
    rotas = f"{base}/api/conexoes-plataforma/github"
    return {
        "name": f"Fabrica {nome}",
        "url": base,
        "hook_attributes": {"url": f"{base}/api/webhooks/github/"},
        "redirect_url": f"{rotas}/retorno/",
        "setup_url": f"{rotas}/instalado/",
        "public": False,
        "default_permissions": {
            "contents": "write",
            "issues": "write",
            "pull_requests": "write",
            "metadata": "read",
            "checks": "read",
            "actions": "read",
        },
        "default_events": [
            "issues",
            "issue_comment",
            "pull_request",
            "pull_request_review",
            "check_suite",
        ],  # fmt: skip
    }


class GitHubAdaptador:
    def __init__(self, conexao):
        credenciais = dict(conexao.credenciais or {})
        self._app_id = str(credenciais.get("app_id") or "")
        self._slug = str(credenciais.get("slug") or "")
        self._pem = str(credenciais.get("pem") or "")
        self._installation_id = str((conexao.config or {}).get("installation_id") or "")

    # --- autenticação -------------------------------------------------------------------

    def _jwt(self) -> str:
        agora = int(time.time())
        carga = {"iat": agora - 60, "exp": agora + 540, "iss": self._app_id}
        try:
            return jwt.encode(carga, self._pem, algorithm="RS256")
        except jwt.PyJWTError, ValueError, TypeError:
            raise ErroDePlataforma(MSG_CHAVE) from None

    def token_de_instalacao(self) -> str:
        """Token de curta duração (1 hora) da instalação. Nunca registrar em log."""
        if not self._installation_id:
            raise ErroDePlataforma(self._msg_sem_instalacao())
        resposta = _requisitar(
            "POST", f"{API}/app/installations/{self._installation_id}/access_tokens", self._jwt()
        )
        if resposta.status_code in (401, 403):
            raise ErroDePlataforma(MSG_RECUSADO)
        if resposta.status_code == 404:
            raise ErroDePlataforma(
                "A instalação do App no GitHub não existe mais. Remova esta conexão e "
                "crie-a de novo."
            )
        if resposta.status_code not in (200, 201):
            raise ErroDePlataforma(
                f"O GitHub respondeu com erro (HTTP {resposta.status_code}). "
                "Tente de novo em instantes."
            )
        try:
            token = resposta.json().get("token")
        except ValueError, AttributeError:
            token = None
        if not isinstance(token, str) or not token:
            raise ErroDePlataforma("O GitHub devolveu uma resposta inesperada. Tente de novo.")
        return token

    def _msg_sem_instalacao(self) -> str:
        return (
            "O App do GitHub ainda não foi instalado. Instale-o em "
            f"{link_de_instalacao(self._slug)} escolhendo os repositórios."
        )

    def instalacao_pertence_ao_app(self, installation_id: str) -> bool:
        """Confere, com o JWT do App, que a instalação é deste App (e não de outro)."""
        resposta = _requisitar("GET", f"{API}/app/installations/{installation_id}", self._jwt())
        if resposta.status_code in (401, 403):
            raise ErroDePlataforma(MSG_RECUSADO)
        if resposta.status_code == 404:
            return False
        if resposta.status_code != 200:
            raise ErroDePlataforma(
                f"O GitHub respondeu com erro (HTTP {resposta.status_code}). "
                "Tente de novo em instantes."
            )
        try:
            return str(resposta.json().get("app_id")) == self._app_id
        except ValueError, AttributeError:
            return False

    # --- contrato AdaptadorPlataforma ---------------------------------------------------

    def testar(self) -> ResultadoTeste:
        try:
            if not self._installation_id:
                resposta = _requisitar("GET", f"{API}/app", self._jwt())
                if resposta.status_code in (401, 403):
                    raise ErroDePlataforma(MSG_RECUSADO)
                if resposta.status_code != 200:
                    raise ErroDePlataforma(
                        f"O GitHub respondeu com erro (HTTP {resposta.status_code}). "
                        "Tente de novo em instantes."
                    )
                return ResultadoTeste(
                    ok=False,
                    status="falha",
                    mensagem="O App existe, mas ainda não foi instalado. "
                    f"Instale-o em {link_de_instalacao(self._slug)} escolhendo os repositórios.",
                )
            self.token_de_instalacao()
        except ErroDePlataforma as erro:
            return ResultadoTeste(ok=False, status="falha", mensagem=str(erro))
        return ResultadoTeste(
            ok=True, status="ok", mensagem=f"Conectado ao GitHub pelo App «{self._slug}»."
        )

    def listar_repositorios(self) -> list[Repositorio]:
        token = self.token_de_instalacao()
        url: str | None = f"{API}/installation/repositories?per_page={POR_PAGINA}"
        repositorios: list[Repositorio] = []
        for _ in range(MAX_PAGINAS):
            if url is None:
                break
            resposta = self._ler(_requisitar("GET", url, token))
            try:
                itens = resposta.json()["repositories"]
                repositorios += [
                    Repositorio(str(r["id"]), r["full_name"], r["html_url"]) for r in itens
                ]
            except ValueError, KeyError, TypeError:
                raise ErroDePlataforma(
                    "O GitHub devolveu uma lista de repositórios inesperada. Tente de novo."
                ) from None
            url = self._proxima_pagina(resposta)
        return repositorios

    @staticmethod
    def _proxima_pagina(resposta) -> str | None:
        destino = resposta.links.get("next", {}).get("url")
        # Só segue o link se for da API do GitHub: o token nunca vai para outro host.
        if destino and urlparse(destino).netloc == urlparse(API).netloc:
            return destino
        return None

    @staticmethod
    def _ler(resposta):
        if resposta.status_code in (401, 403):
            raise ErroDePlataforma(MSG_RECUSADO)
        if resposta.status_code != 200:
            raise ErroDePlataforma(
                f"O GitHub respondeu com erro (HTTP {resposta.status_code}). "
                "Tente de novo em instantes."
            )
        return resposta

    def conferir(
        self, repo: Repositorio, url_webhook: str, etiquetas: list[Etiqueta]
    ) -> list[ItemConferencia]:
        instalado = self._item_instalacao(repo)
        if not instalado.ok:
            return [
                instalado,
                self._item_webhook(url_webhook),
                ItemConferencia(
                    "etiquetas",
                    "Etiquetas",
                    False,
                    "Não dá para conferir as etiquetas antes de instalar o App no repositório.",
                    False,
                ),
            ]
        faltando = self._etiquetas_faltando(repo, etiquetas)
        return [instalado, self._item_etiquetas(faltando), self._item_webhook(url_webhook)]

    def preparar(
        self, repo: Repositorio, url_webhook: str, etiquetas: list[Etiqueta]
    ) -> list[ItemConferencia]:
        instalado = self._item_instalacao(repo)
        if not instalado.ok:
            return self.conferir(repo, url_webhook, etiquetas)
        token = self.token_de_instalacao()
        faltando = self._etiquetas_faltando(repo, etiquetas, token)
        item_etiquetas = self._item_etiquetas(self._criar_etiquetas(repo, faltando, token))
        item_webhook = self._item_webhook(url_webhook)
        if not item_webhook.ok:
            item_webhook = self._corrigir_webhook(url_webhook)
        return [instalado, item_etiquetas, item_webhook]

    # --- itens da conferência -----------------------------------------------------------

    def _item_instalacao(self, repo: Repositorio) -> ItemConferencia:
        titulo = "App instalado no repositório"
        try:
            instalados = {r.id_externo for r in self.listar_repositorios()}
        except ErroDePlataforma as erro:
            if not self._installation_id:
                instalados = set()
            else:
                return ItemConferencia("app_instalado_no_repo", titulo, False, str(erro), False)
        if repo.id_externo in instalados:
            return ItemConferencia("app_instalado_no_repo", titulo, True, "App instalado.", False)
        return ItemConferencia(
            "app_instalado_no_repo",
            titulo,
            False,
            f"O App não está instalado neste repositório. Instale-o em "
            f"{link_de_instalacao(self._slug)} e inclua {repo.caminho}.",
            False,
        )

    def _etiquetas_faltando(
        self, repo: Repositorio, etiquetas: list[Etiqueta], token: str | None = None
    ) -> list[Etiqueta]:
        token = token or self.token_de_instalacao()
        existentes: set[str] = set()
        url: str | None = f"{API}/repos/{repo.caminho}/labels?per_page={POR_PAGINA}"
        for _ in range(MAX_PAGINAS):
            if url is None:
                break
            resposta = self._ler(_requisitar("GET", url, token))
            try:
                existentes |= {e["name"].lower() for e in resposta.json()}
            except ValueError, KeyError, TypeError, AttributeError:
                raise ErroDePlataforma(
                    "O GitHub devolveu uma lista de etiquetas inesperada. Tente de novo."
                ) from None
            url = self._proxima_pagina(resposta)
        return [e for e in etiquetas if e.nome.lower() not in existentes]

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

    def _criar_etiquetas(
        self, repo: Repositorio, faltando: list[Etiqueta], token: str
    ) -> list[Etiqueta]:
        """Cria as etiquetas. 422 `already_exists` conta como ok. Devolve as que não deram."""
        sobraram = []
        for etiqueta in faltando:
            resposta = _requisitar(
                "POST",
                f"{API}/repos/{repo.caminho}/labels",
                token,
                json={
                    "name": etiqueta.nome,
                    "color": etiqueta.cor,
                    "description": etiqueta.descricao,
                },
            )
            if resposta.status_code == 201 or self._ja_existe(resposta):
                continue
            sobraram.append(etiqueta)
        return sobraram

    @staticmethod
    def _ja_existe(resposta) -> bool:
        if resposta.status_code != 422:
            return False
        try:
            erros = resposta.json().get("errors", [])
            return any(e.get("code") == "already_exists" for e in erros)
        except ValueError, AttributeError, TypeError:
            return False

    def _item_webhook(self, url_webhook: str) -> ItemConferencia:
        try:
            resposta = self._ler(_requisitar("GET", f"{API}/app/hook/config", self._jwt()))
            config = resposta.json()
            url, tipo = config.get("url"), config.get("content_type")
        except ErroDePlataforma as erro:
            return ItemConferencia("webhook", "Webhook", False, str(erro), False)
        except ValueError, AttributeError:
            return ItemConferencia(
                "webhook", "Webhook", False, "O GitHub devolveu uma configuração inesperada.", False
            )
        if url == url_webhook and tipo == "json":
            return ItemConferencia("webhook", "Webhook", True, "Webhook configurado.", True)
        return ItemConferencia(
            "webhook",
            "Webhook",
            False,
            "O webhook do App aponta para outro endereço ou não envia JSON. Use «Preparar».",
            True,
        )

    def _corrigir_webhook(self, url_webhook: str) -> ItemConferencia:
        try:
            resposta = _requisitar(
                "PATCH",
                f"{API}/app/hook/config",
                self._jwt(),
                json={"url": url_webhook, "content_type": "json"},
            )
        except ErroDePlataforma as erro:
            return ItemConferencia("webhook", "Webhook", False, str(erro), True)
        if resposta.status_code == 200:
            return ItemConferencia("webhook", "Webhook", True, "Webhook corrigido.", True)
        return ItemConferencia(
            "webhook",
            "Webhook",
            False,
            f"Não consegui corrigir o webhook (HTTP {resposta.status_code}). Tente de novo.",
            True,
        )
