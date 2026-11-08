import pytest

from apps.donos.models import Dono
from apps.fluxos import servicos
from apps.fluxos.models import Predefinicao
from apps.plataformas.models import ConexaoPlataforma
from apps.projetos.models import Projeto

BASE = "/api/predefinicoes/"


def _json(client, metodo, url, corpo=None):
    return getattr(client, metodo)(url, corpo, content_type="application/json")


@pytest.fixture
def contas(dono, conta_factory):
    return conta_factory(dono=dono), conta_factory(dono=dono)


@pytest.fixture
def padrao(dono, contas):
    return servicos.criar_padrao(dono, *contas)


@pytest.fixture
def conexao(dono):
    return ConexaoPlataforma.objects.create(
        dono=dono, nome="GL", tipo="gitlab", url_base="https://g.exemplo.com"
    )


def _projeto(dono, conexao, predefinicao, cliente=None, n=1):
    return Projeto.objects.create(
        dono=dono,
        nome=f"P{n}",
        conexao=conexao,
        repositorio_caminho="a/b",
        repositorio_id_externo=str(n),
        repositorio_url="https://g/a/b",
        cliente=cliente,
        predefinicao=predefinicao,
    )


def test_exige_login(client, db):
    assert client.get(BASE).status_code == 403
    assert client.get("/api/etapas-e-gatilhos/").status_code == 403


def test_etapas_e_gatilhos(client, logado):
    r = client.get("/api/etapas-e-gatilhos/")
    assert r.status_code == 200
    corpo = r.json()
    assert [e["chave"] for e in corpo["etapas"]] == servicos.ETAPAS
    assert [g["chave"] for g in corpo["gatilhos"]] == servicos.GATILHOS
    assert [m["chave"] for m in corpo["metodos"]] == ["superpowers"]
    assert all(e["rotulo"] for e in corpo["etapas"] + corpo["gatilhos"] + corpo["metodos"])


def test_criar_listar_e_ler(client, logado, padrao):
    corpo = {"nome": "Minha", "descricao": "d", "metodo": "superpowers", "etapas": padrao.etapas}
    r = _json(client, "post", BASE, corpo)
    assert r.status_code == 201, r.content
    novo = r.json()
    assert novo["merge_autonomo"] is True
    assert {"id", "nome", "descricao", "metodo", "etapas", "merge_autonomo"} <= set(novo)
    lista = client.get(BASE).json()
    assert {p["nome"] for p in _itens(lista)} == {"Padrão", "Minha"}
    assert client.get(f"{BASE}{novo['id']}/").status_code == 200


def _itens(lista):
    return lista["results"] if isinstance(lista, dict) else lista


def test_criar_com_etapas_invalidas_da_400_em_pt_br(client, logado):
    r = _json(client, "post", BASE, {"nome": "x", "etapas": [{"chave": "implementar"}]})
    assert r.status_code == 400
    assert "etapas" in r.json()


@pytest.mark.parametrize("etapas", [None, "x", 5, {"a": 1}, [1], [[]], [{"chave": {}}]])
def test_etapas_malformadas_nao_sao_500(client, logado, etapas):
    r = _json(client, "post", BASE, {"nome": "x", "etapas": etapas})
    assert r.status_code == 400


def test_metodo_desconhecido_da_400(client, logado, padrao):
    r = _json(client, "post", BASE, {"nome": "x", "metodo": "spec-kit", "etapas": padrao.etapas})
    assert r.status_code == 400
    assert "Método desconhecido: spec-kit." in str(r.json())


def test_conta_de_outro_dono_da_400(client, logado, conta_factory, padrao):
    alheia = conta_factory(dono=Dono.objects.create(nome="Outro"))
    etapas = [dict(e) for e in padrao.etapas]
    etapas[1] = {**etapas[1], "papel": {"tipo": "conta", "conta_id": str(alheia.id)}}
    r = _json(client, "post", BASE, {"nome": "x", "etapas": etapas})
    assert r.status_code == 400


def test_outro_dono_nao_ve_a_predefinicao(client, logado, db):
    outro = Dono.objects.create(nome="Outro")
    p = Predefinicao.objects.create(dono=outro, nome="Alheia", etapas=[])
    assert client.get(f"{BASE}{p.id}/").status_code == 404
    assert _itens(client.get(BASE).json()) == []


def test_endpoint_padrao(client, logado, contas):
    executor, revisor = contas
    r = _json(
        client, "post", f"{BASE}padrao/", {"executor": str(executor.id), "revisor": str(revisor.id)}
    )
    assert r.status_code == 201, r.content
    assert [e["chave"] for e in r.json()["etapas"]] == servicos.ETAPAS


def test_endpoint_padrao_com_conta_alheia_da_400(client, logado, contas, conta_factory):
    alheia = conta_factory()
    r = _json(
        client, "post", f"{BASE}padrao/", {"executor": str(alheia.id), "revisor": str(contas[1].id)}
    )
    assert r.status_code == 400


def test_endpoint_duplicar(client, logado, padrao):
    r = _json(client, "post", f"{BASE}{padrao.id}/duplicar/", {"nome": "Cópia"})
    assert r.status_code == 201
    assert r.json()["nome"] == "Cópia"
    assert r.json()["id"] != str(padrao.id)
    assert r.json()["etapas"] == padrao.etapas


def test_patch_da_predefinicao_valida_projetos_que_usam(
    client, logado, dono, padrao, conexao, conta_factory, cliente_x, cliente_y
):
    _projeto(dono, conexao, padrao, cliente=cliente_x)
    da_y = conta_factory(dono=dono, cliente=cliente_y, nome="Conta do Y")
    etapas = [dict(e) for e in padrao.etapas]
    etapas[1] = {**etapas[1], "papel": {"tipo": "conta", "conta_id": str(da_y.id)}}

    r = _json(client, "patch", f"{BASE}{padrao.id}/", {"etapas": etapas})

    assert r.status_code == 400
    assert "A conta Conta do Y é do cliente Y e não pode trabalhar neste projeto." in str(r.json())
    padrao.refresh_from_db()
    assert padrao.etapas != etapas  # nada foi gravado


def test_patch_valido_grava(client, logado, dono, padrao, conexao, cliente_x):
    _projeto(dono, conexao, padrao, cliente=cliente_x)
    r = _json(
        client, "patch", f"{BASE}{padrao.id}/", {"nome": "Novo nome", "merge_autonomo": False}
    )
    assert r.status_code == 200
    padrao.refresh_from_db()
    assert padrao.nome == "Novo nome" and padrao.merge_autonomo is False


def test_apagar_em_uso_da_400(client, logado, dono, padrao, conexao):
    _projeto(dono, conexao, padrao, n=1)
    _projeto(dono, conexao, padrao, n=2)
    r = client.delete(f"{BASE}{padrao.id}/")
    assert r.status_code == 400
    assert r.json() == {"detail": "Esta predefinição é usada por 2 projeto(s)."}
    assert Predefinicao.objects.filter(pk=padrao.pk).exists()


def test_apagar_sem_uso(client, logado, padrao):
    assert client.delete(f"{BASE}{padrao.id}/").status_code == 204


# predefinição dentro do projeto


def test_projeto_patch_com_predefinicao_e_validacao(
    client, logado, dono, padrao, conexao, conta_factory, cliente_x, cliente_y
):
    projeto = _projeto(dono, conexao, None, cliente=cliente_x)
    r = _json(client, "patch", f"/api/projetos/{projeto.id}/", {"predefinicao": str(padrao.id)})
    assert r.status_code == 200, r.content
    assert r.json()["predefinicao"] == str(padrao.id)

    # trocar para um cliente cuja conta não vale
    da_y = conta_factory(dono=dono, cliente=cliente_y)
    p2 = servicos.criar_padrao(dono, da_y, da_y)
    r = _json(client, "patch", f"/api/projetos/{projeto.id}/", {"predefinicao": str(p2.id)})
    assert r.status_code == 400
    assert "não pode trabalhar neste projeto" in str(r.json())


def test_projeto_patch_de_cliente_revalida_contas(
    client, logado, dono, conta_factory, conexao, cliente_x, cliente_y
):
    da_x = conta_factory(dono=dono, cliente=cliente_x)
    pred = servicos.criar_padrao(dono, da_x, da_x)
    projeto = _projeto(dono, conexao, pred, cliente=cliente_x)
    r = _json(client, "patch", f"/api/projetos/{projeto.id}/", {"cliente": str(cliente_y.id)})
    assert r.status_code == 400


def test_projeto_com_predefinicao_de_outro_dono_da_400(client, logado, dono, conexao):
    alheia = Predefinicao.objects.create(dono=Dono.objects.create(nome="O"), nome="A", etapas=[])
    projeto = _projeto(dono, conexao, None)
    r = _json(client, "patch", f"/api/projetos/{projeto.id}/", {"predefinicao": str(alheia.id)})
    assert r.status_code == 400


def test_api_nao_guarda_chaves_extras(client, logado, padrao):
    etapas = [dict(e) for e in padrao.etapas]
    etapas[0] = {**etapas[0], "extra": "x", "papel": {"tipo": "central", "conta_id": "lixo"}}
    r = _json(client, "post", BASE, {"nome": "x", "etapas": etapas})
    assert r.status_code == 201, r.content
    assert "extra" not in r.json()["etapas"][0]
    assert r.json()["etapas"][0]["papel"] == {"tipo": "central"}


def test_api_ordem_errada_da_400(client, logado, padrao):
    r = _json(client, "post", BASE, {"nome": "x", "etapas": list(reversed(padrao.etapas))})
    assert r.status_code == 400
    assert "ordem" in str(r.json())


def test_projeto_patch_so_de_cliente_reporta_em_cliente(
    client, logado, dono, conta_factory, conexao, cliente_x, cliente_y
):
    da_x = conta_factory(dono=dono, cliente=cliente_x)
    pred = servicos.criar_padrao(dono, da_x, da_x)
    projeto = _projeto(dono, conexao, pred, cliente=cliente_x)
    r = _json(client, "patch", f"/api/projetos/{projeto.id}/", {"cliente": str(cliente_y.id)})
    assert r.status_code == 400
    assert "cliente" in r.json() and "predefinicao" not in r.json()
