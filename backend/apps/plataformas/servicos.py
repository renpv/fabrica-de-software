"""Regras de negócio das conexões com plataformas. Views e API só chamam este módulo.

O fluxo do GitHub (manifest flow) tem dois redirecionamentos do navegador que voltam para a
central. Cada um carrega um `state` assinado (django.core.signing, validade de 1 hora) com o id
do dono, um nonce e, na instalação, o id da conexão. Sais diferentes impedem usar o state de um
passo no outro.
"""

import re
import secrets
import uuid
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.core import signing
from django.core.cache import cache

from .adaptadores import github, obter_adaptador
from .adaptadores.base import ErroDePlataforma, Repositorio, ResultadoTeste
from .adaptadores.gitlab import MSG_TOKEN_INVALIDO, token_valido
from .erros import MENSAGENS_DE_ERRO
from .models import ConexaoPlataforma

SAL_MANIFESTO = "plataformas.github.manifesto"
SAL_INSTALACAO = "plataformas.github.instalacao"
VALIDADE_STATE_SEGUNDOS = 3600
CODIGO_VALIDO = re.compile(r"^[A-Za-z0-9_-]{1,200}$")
ID_INSTALACAO_VALIDO = re.compile(r"^[0-9]{1,20}$")


class ErroDeFluxo(Exception):
    """Pedido recusado no fluxo de conexão. `codigo` é uma chave de `MENSAGENS_DE_ERRO`."""

    def __init__(self, codigo: str):
        super().__init__(MENSAGENS_DE_ERRO[codigo])
        self.codigo = codigo


class ConexaoRecusada(Exception):
    """Dados de conexão recusados (formato ou teste). A mensagem é pt-BR, sem segredo."""


MSG_URL_INVALIDA = (
    "O endereço do GitLab é inválido. Use algo como https://gitlab.suaempresa.com.br, "
    "sem usuário, senha nem parâmetros."
)


def normalizar_url_gitlab(texto: str) -> str:
    """Devolve `https://host[/caminho]` sem barra no fim e sem `/api/v4`.

    Sem esquema, assume `https://`. Levanta ValueError (pt-BR) se o endereço não serve.
    """
    texto = (texto or "").strip()
    if not texto:
        raise ValueError(MSG_URL_INVALIDA)
    if "://" not in texto:
        texto = f"https://{texto}"
    try:
        partes = urlsplit(texto)
        host, _ = partes.hostname, partes.port
    except ValueError:
        raise ValueError(MSG_URL_INVALIDA) from None
    if (
        partes.scheme not in ("http", "https")
        or not host
        or partes.username is not None
        or partes.password is not None
        or partes.query
        or partes.fragment
    ):
        raise ValueError(MSG_URL_INVALIDA)
    caminho = partes.path.rstrip("/").removesuffix("/api/v4").rstrip("/")
    return f"{partes.scheme}://{partes.netloc}{caminho}"


def url_webhook_gitlab(conexao: ConexaoPlataforma) -> str:
    base = settings.FABRICA_URL_PUBLICA.rstrip("/")
    return f"{base}/api/webhooks/gitlab/{conexao.id}/"


def criar_conexao_gitlab(dono, nome: str, url_base: str, token: str) -> ConexaoPlataforma:
    """Valida, testa e só então grava a conexão. Levanta ConexaoRecusada (pt-BR)."""
    try:
        url = normalizar_url_gitlab(url_base)
    except ValueError as erro:
        raise ConexaoRecusada(str(erro)) from None
    token = (token or "").strip()
    if not token_valido(token):
        raise ConexaoRecusada(MSG_TOKEN_INVALIDO)
    conexao = ConexaoPlataforma(
        dono=dono,
        nome=nome,
        tipo="gitlab",
        url_base=url,
        credenciais={"token": token, "webhook_secret": secrets.token_urlsafe(32)},
    )
    resultado = obter_adaptador(conexao).testar()
    if not resultado.ok:
        raise ConexaoRecusada(resultado.mensagem)
    conexao.status = resultado.status
    conexao.ultimo_teste_mensagem = resultado.mensagem[
        : conexao._meta.get_field("ultimo_teste_mensagem").max_length
    ]
    conexao.save()
    return conexao


def url_front() -> str:
    return settings.FABRICA_URL_PUBLICA.rstrip("/") + "/plataformas"


def url_de_erro(codigo: str) -> str:
    """Destino do redirecionamento de falha: a tela de plataformas e um código fixo."""
    if codigo not in MENSAGENS_DE_ERRO:
        codigo = "github_fora_do_ar"
    return f"{url_front()}?{urlencode({'erro': codigo})}"


def _ler_state(state: str, sal: str, dono) -> dict:
    try:
        carga = signing.loads(state, salt=sal, max_age=VALIDADE_STATE_SEGUNDOS)
    except signing.BadSignature:
        raise ErroDeFluxo("estado_invalido") from None
    if not isinstance(carga, dict) or carga.get("d") != str(dono.id) or not carga.get("n"):
        raise ErroDeFluxo("estado_invalido")
    return carga


def _chave_nonce(carga: dict) -> str:
    return f"plataformas:state:{carga['n']}"


def _consumir_nonce(carga: dict) -> None:
    """Marca o state como usado: ele vale uma vez só. Reuso vira `estado_invalido`."""
    if not cache.add(_chave_nonce(carga), 1, VALIDADE_STATE_SEGUNDOS):
        raise ErroDeFluxo("estado_invalido")


def gerar_manifesto(dono, nome: str) -> dict:
    """Devolve a URL do GitHub e o manifesto para o front enviar por formulário (POST)."""
    state = signing.dumps(
        {"d": str(dono.id), "n": secrets.token_urlsafe(16), "nm": nome}, salt=SAL_MANIFESTO
    )
    return {
        "acao": f"https://github.com/settings/apps/new?{urlencode({'state': state})}",
        "manifesto": github.montar_manifesto(nome, settings.FABRICA_URL_PUBLICA),
    }


def concluir_manifesto(dono, codigo: str, state: str) -> str:
    """Troca o código pelas credenciais, grava a conexão e devolve a URL de instalação."""
    carga = _ler_state(state, SAL_MANIFESTO, dono)
    if not CODIGO_VALIDO.fullmatch(codigo or ""):
        raise ErroDeFluxo("conversao_falhou")
    _consumir_nonce(carga)  # o code do GitHub também é de uso único: sem nova tentativa
    try:
        credenciais = github.converter_manifesto(codigo)
    except ErroDePlataforma as erro:
        raise ErroDeFluxo(erro.codigo) from None
    nome = str(carga.get("nm") or "GitHub")[:120]
    try:
        conexao = ConexaoPlataforma.objects.create(
            dono=dono, nome=nome, tipo="github", credenciais=credenciais, config={}
        )
    except Exception:
        # O App já existe no GitHub e a chave privada só veio uma vez: a pessoa precisa apagá-lo.
        raise ErroDeFluxo("conversao_sem_registro") from None
    proximo = signing.dumps(
        {"d": str(dono.id), "n": secrets.token_urlsafe(16), "c": str(conexao.id)},
        salt=SAL_INSTALACAO,
    )
    # O destino é montado só com o slug que o GitHub devolveu (já validado) e o state nosso.
    return f"{github.link_de_instalacao(credenciais['slug'])}?{urlencode({'state': proximo})}"


def concluir_instalacao(dono, installation_id: str, state: str) -> str:
    """Confere que a instalação é do App desta conexão, grava o id e devolve o destino no front."""
    carga = _ler_state(state, SAL_INSTALACAO, dono)
    if not ID_INSTALACAO_VALIDO.fullmatch(installation_id or ""):
        raise ErroDeFluxo("instalacao_invalida")
    conexao = (
        ConexaoPlataforma.objects.filter(dono=dono, pk=carga.get("c"), tipo="github").first()
        if _uuid_valido(carga.get("c"))
        else None
    )
    if conexao is None:
        raise ErroDeFluxo("estado_invalido")
    _consumir_nonce(carga)
    try:
        pertence = obter_adaptador(conexao).instalacao_pertence_ao_app(installation_id)
    except ErroDePlataforma as erro:
        cache.delete(_chave_nonce(carga))  # falha do lado do GitHub: pode tentar de novo
        raise ErroDeFluxo(erro.codigo) from None
    if not pertence:
        raise ErroDeFluxo("instalacao_invalida")
    conexao.config = {**conexao.config, "installation_id": installation_id}
    conexao.save(update_fields=["config", "atualizado_em"])
    return url_front()


def _uuid_valido(valor) -> bool:
    try:
        uuid.UUID(str(valor))
    except ValueError:
        return False
    return True


def testar_conexao(conexao: ConexaoPlataforma) -> ResultadoTeste:
    """Testa a conexão e grava o resultado nela."""
    resultado = obter_adaptador(conexao).testar()
    conexao.status = resultado.status
    limite = conexao._meta.get_field("ultimo_teste_mensagem").max_length
    conexao.ultimo_teste_mensagem = resultado.mensagem[:limite]
    conexao.save(update_fields=["status", "ultimo_teste_mensagem", "atualizado_em"])
    return resultado


def listar_repositorios(conexao: ConexaoPlataforma) -> list[Repositorio]:
    """Todos os repositórios acessíveis pela conexão. Levanta ErroDePlataforma (pt-BR)."""
    return obter_adaptador(conexao).listar_repositorios()


def excluir_conexao(conexao: ConexaoPlataforma) -> None:
    conexao.delete()


__all__ = [
    "ConexaoRecusada",
    "ErroDeFluxo",
    "ErroDePlataforma",
    "MENSAGENS_DE_ERRO",
    "concluir_instalacao",
    "concluir_manifesto",
    "criar_conexao_gitlab",
    "excluir_conexao",
    "gerar_manifesto",
    "listar_repositorios",
    "normalizar_url_gitlab",
    "testar_conexao",
    "url_de_erro",
    "url_webhook_gitlab",
]
