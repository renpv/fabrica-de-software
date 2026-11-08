"""Adaptador do GitLab (instância self-hosted) por token de acesso pessoal ou de projeto/grupo.

O token vai só no cabeçalho `PRIVATE-TOKEN`, sempre para a URL da própria conexão. Nenhum
segredo, token nem corpo de resposta do GitLab entra em log ou em mensagem de erro, e as
chamadas não seguem redirecionamentos (o token não sai da instância).
"""

import ipaddress
import socket
from urllib.parse import urlsplit

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
MSG_INTERNO = (
    "Esse endereço aponta para a própria central ou para uma rede reservada. "
    "Use o endereço do GitLab da sua instituição."
)
COD_INTERNO = "gitlab_endereco_interno"
MSG_INESPERADA = "O GitLab devolveu uma resposta inesperada. Tente de novo."


def token_valido(token) -> bool:
    return (
        isinstance(token, str)
        and bool(token)
        and token.isascii()
        and token.isprintable()
        and " " not in token
    )


_REDES_PROIBIDAS = (
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT (inclui 100.100.100.200, metadados da Alibaba)
    ipaddress.ip_network("fd00:ec2::254/128"),  # metadados da AWS por IPv6
    ipaddress.ip_network("100.100.100.200/32"),
)
_NAT64 = ipaddress.ip_network("64:ff9b::/96")


def _candidatos(ip) -> list:
    """O próprio IP e os IPv4 embutidos nele (mapeado, 6to4, Teredo, NAT64)."""
    candidatos = [ip]
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            candidatos.append(ip.ipv4_mapped)
        if ip.sixtofour is not None:
            candidatos.append(ip.sixtofour)
        if ip.teredo is not None:
            candidatos.extend(ip.teredo)  # (servidor, cliente)
        if ip in _NAT64:
            candidatos.append(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF))
    return candidatos


def _ip_proibido(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    # Redes privadas (RFC 1918, ULA) ficam permitidas: o GitLab pode estar na rede interna.
    for c in _candidatos(ip):
        if (
            c.is_loopback
            or c.is_link_local
            or c.is_multicast
            or c.is_reserved
            or c.is_unspecified
            or any(c.version == r.version and c in r for r in _REDES_PROIBIDAS)
        ):
            return True
    return False


def resolver_destino(url: str) -> str:
    """Resolve o host UMA vez e devolve o IP escolhido (literal, pronto para uso em URL).

    Todo endereço devolvido pelo DNS precisa passar na checagem; quem conecta usa este IP,
    então o DNS não pode mudar entre a checagem e a conexão. Falha de resolução levanta a
    mensagem de rede (a mesma de qualquer falha de conexão). A mensagem nunca mostra o IP."""
    partes = urlsplit(url)
    msg_rede = ErroDePlataforma(
        f"Não consegui acessar {url}. "
        "Confira o endereço e se a central alcança a rede da instância.",
        COD_FORA_DO_AR,
    )
    try:
        porta = partes.port or (443 if partes.scheme == "https" else 80)
        infos = socket.getaddrinfo(partes.hostname, porta, type=socket.SOCK_STREAM)
        enderecos = [ipaddress.ip_address(i[4][0].split("%")[0]) for i in infos]
    except OSError, ValueError, UnicodeError:
        raise msg_rede from None
    if not enderecos:
        raise msg_rede
    if any(_ip_proibido(ip) for ip in enderecos):
        raise ErroDePlataforma(MSG_INTERNO, COD_INTERNO)
    ip = enderecos[0]
    return f"[{ip}]" if ip.version == 6 else str(ip)


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
        # Uma resolução por chamada; a conexão vai direto ao IP conferido (sem novo DNS).
        ip = resolver_destino(self._url)
        original = urlsplit(self._url)
        netloc = f"{ip}:{original.port}" if original.port else ip
        url = f"{original.scheme}://{netloc}{original.path}/api/v4{caminho}"
        extensoes = {"sni_hostname": original.hostname} if original.scheme == "https" else {}
        try:
            # trust_env=False: proxy do ambiente faria o DNS por fora do IP conferido.
            with httpx.Client(
                timeout=TIMEOUT_SEGUNDOS, follow_redirects=False, trust_env=False
            ) as cliente:
                return cliente.request(
                    metodo,
                    url,
                    headers={"PRIVATE-TOKEN": self._token, "Host": original.netloc},
                    extensions=extensoes,
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
        self._criar_etiquetas(repo, faltando)
        existe = self._tem_webhook(repo, url_webhook)
        if not existe:
            existe = self._criar_webhook(repo, url_webhook)
        return [self._item_etiquetas([]), self._item_webhook(existe)]

    # --- etiquetas ----------------------------------------------------------------------

    def _etiquetas_faltando(self, repo: Repositorio, etiquetas: list[Etiqueta]) -> list[Etiqueta]:
        existentes: set[str] = set()
        for pagina in self._paginas(f"/projects/{repo.id_externo}/labels"):
            try:
                existentes |= {e["name"].lower() for e in pagina}
            except KeyError, TypeError, AttributeError:
                raise _inesperada() from None
        return [e for e in etiquetas if e.nome.lower() not in existentes]

    def _criar_etiquetas(self, repo: Repositorio, faltando: list[Etiqueta]) -> None:
        """Cria as etiquetas. 409 (já existe) conta como ok. Qualquer outra falha sobe como erro."""
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
                raise erro_de_status(resposta)

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
        """Cria o webhook. 422 é o GitLab recusando a URL; outras falhas sobem como erro."""
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
        if resposta.status_code == 422:
            raise ErroDePlataforma(
                "O GitLab recusou o endereço do webhook. Peça ao administrador da instância "
                f"para liberar requisições para {urlsplit(url_webhook).netloc}.",
                COD_FORA_DO_AR,
            )
        if resposta.status_code != 201:
            raise erro_de_status(resposta)
        return True

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
