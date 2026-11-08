import pytest

from apps.donos.models import Dono
from apps.projetos import servicos
from apps.projetos.models import Projeto

pytestmark = pytest.mark.django_db


def _criar(conexao, **extra):
    return servicos.criar_projeto(
        conexao.dono, nome="Meu projeto", conexao=conexao, repositorio_id_externo="42", **extra
    )


def test_etiquetas_de_todos_os_agentes():
    nomes = [e.nome for e in servicos.etiquetas_do_projeto()]
    assert "acao:implementar" in nomes
    assert "agente:claude" in nomes
    assert "agente:cursor" in nomes


def test_preparar_inclui_etiquetas_de_todos_os_agentes(conexao, adaptador_falso):
    projeto = _criar(conexao)

    _, repo, url, etiquetas = adaptador_falso.chamadas[-1]
    nomes = {e.nome for e in etiquetas}
    assert {"agente:claude", "agente:cursor", "acao:implementar"} <= nomes
    assert repo.caminho == "grupo/projeto"
    assert url == f"http://localhost:8000/api/webhooks/gitlab/{conexao.id}/"
    assert servicos.url_webhook(projeto) == url


def test_criar_projeto_ja_prepara(conexao, adaptador_falso):
    projeto = _criar(conexao)

    assert adaptador_falso.chamadas[-1][0] == "preparar"
    projeto.refresh_from_db()
    assert projeto.repositorio_caminho == "grupo/projeto"
    assert projeto.repositorio_url == "https://git.exemplo.com/grupo/projeto"
    assert projeto.ultima_conferencia[0]["chave"] == "webhook"
    assert projeto.ultima_conferencia_em is not None


def test_conferir_grava_resultado(conexao, adaptador_falso):
    projeto = _criar(conexao)
    Projeto.objects.filter(pk=projeto.pk).update(ultima_conferencia=[], ultima_conferencia_em=None)
    projeto.refresh_from_db()

    itens = servicos.conferir_projeto(projeto)

    assert adaptador_falso.chamadas[-1][0] == "conferir"
    projeto.refresh_from_db()
    assert projeto.ultima_conferencia == [
        {"chave": "webhook", "titulo": "Webhook", "ok": True,
         "mensagem": "Webhook configurado.", "consertavel": True}
    ]  # fmt: skip
    assert projeto.ultima_conferencia_em is not None
    assert itens[0].ok


def test_repositorio_inacessivel(conexao, adaptador_falso):
    with pytest.raises(servicos.ErroDeProjeto):
        servicos.criar_projeto(
            conexao.dono, nome="x", conexao=conexao, repositorio_id_externo="999"
        )
    assert not Projeto.objects.exists()


def test_caminho_invalido_da_listagem_e_recusado(conexao, adaptador_falso):
    from apps.plataformas.adaptadores.base import Repositorio

    adaptador_falso.repositorios = [Repositorio("7", "a/b?x=1", "https://x/y")]
    with pytest.raises(servicos.ErroDeProjeto):
        servicos.criar_projeto(conexao.dono, nome="x", conexao=conexao, repositorio_id_externo="7")
    assert not Projeto.objects.exists()


def test_grupos_aninhados_sao_aceitos(conexao, adaptador_falso):
    from apps.plataformas.adaptadores.base import Repositorio

    adaptador_falso.repositorios = [Repositorio("8", "a/b/c.d", "https://x/a/b/c.d")]
    projeto = servicos.criar_projeto(
        conexao.dono, nome="x", conexao=conexao, repositorio_id_externo="8"
    )
    assert projeto.repositorio_caminho == "a/b/c.d"


def test_conexao_de_outro_dono_e_recusada(conexao, adaptador_falso):
    outro = Dono.objects.create(nome="Outro")
    with pytest.raises(servicos.ErroDeProjeto):
        servicos.criar_projeto(outro, nome="x", conexao=conexao, repositorio_id_externo="42")


def test_repositorio_duplicado_e_recusado(conexao, adaptador_falso):
    _criar(conexao)
    with pytest.raises(servicos.ErroDeProjeto):
        _criar(conexao)


def test_falha_ao_preparar_mantem_o_projeto(conexao, adaptador_falso):
    adaptador_falso.erro_ao_preparar = True

    projeto = _criar(conexao)

    assert Projeto.objects.filter(pk=projeto.pk).exists()
    assert projeto.ultima_conferencia == []
    assert "Tente de novo" in projeto.erro_ao_preparar


def test_corrida_na_criacao_vira_erro_de_projeto(conexao, adaptador_falso, monkeypatch):
    """O duplicado aparece entre a listagem e a gravação: o banco recusa, sem 500."""
    original = adaptador_falso.listar_repositorios

    def lista_e_duplica(self):
        itens = original(self)
        Projeto.objects.create(
            dono=conexao.dono, nome="Outro pedido", conexao=conexao,
            repositorio_caminho="grupo/projeto", repositorio_id_externo="42",
            repositorio_url="https://git.exemplo.com/grupo/projeto",
        )  # fmt: skip
        return itens

    monkeypatch.setattr(adaptador_falso, "listar_repositorios", lista_e_duplica)

    with pytest.raises(servicos.ErroDeProjeto) as erro:
        _criar(conexao)
    assert str(erro.value) == servicos.MSG_DUPLICADO
    assert Projeto.objects.count() == 1
