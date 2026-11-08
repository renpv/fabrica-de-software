import pytest

from apps.donos.models import Dono
from apps.fluxos import servicos
from apps.fluxos.metodos import METODOS, Metodo
from apps.projetos import servicos as projetos_servicos
from apps.projetos.models import Projeto

pytestmark = pytest.mark.django_db


def _etapas(dono, conta, **trocas):
    base = {
        "publicar_tasks": {"papel": {"tipo": "central"}, "gatilho": "anterior_concluida"},
        "implementar": {
            "papel": {"tipo": "conta", "conta_id": str(conta.id)},
            "gatilho": "anterior_concluida",
        },
        "revisar": {
            "papel": {"tipo": "conta", "conta_id": str(conta.id)},
            "gatilho": "anterior_concluida",
        },
        "merge": {"papel": {"tipo": "central"}, "gatilho": "anterior_concluida"},
        "promover": {"papel": {"tipo": "humano"}, "gatilho": "decisao_humana"},
    }
    base.update(trocas)
    return [{"chave": chave, **dados} for chave, dados in base.items()]


def test_constantes_e_metodo():
    assert servicos.ETAPAS == ["publicar_tasks", "implementar", "revisar", "merge", "promover"]
    assert servicos.GATILHOS == ["anterior_concluida", "webhook", "temporizador", "decisao_humana"]
    assert METODOS["superpowers"] == Metodo(
        "superpowers", "superpowers", "docs/superpowers/specs", "docs/superpowers/plans"
    )


def test_padrao_tem_as_cinco_etapas_na_ordem(dono, conta_factory):
    executor, revisor = conta_factory(dono=dono), conta_factory(dono=dono)
    p = servicos.criar_padrao(dono, executor, revisor)

    assert p.nome == "Padrão"
    assert [e["chave"] for e in p.etapas] == servicos.ETAPAS
    por_chave = {e["chave"]: e for e in p.etapas}
    assert por_chave["implementar"]["papel"] == {"tipo": "conta", "conta_id": str(executor.id)}
    assert por_chave["revisar"]["papel"] == {"tipo": "conta", "conta_id": str(revisor.id)}
    assert por_chave["promover"]["gatilho"] == "decisao_humana"
    assert por_chave["promover"]["papel"] == {"tipo": "humano"}
    assert por_chave["merge"]["papel"] == {"tipo": "central"}
    assert all(e["gatilho"] == "anterior_concluida" for e in p.etapas if e["chave"] != "promover")
    assert p.merge_autonomo is True
    assert p.metodo == "superpowers"
    assert servicos.validar_etapas(dono, p.etapas) == []


def test_padrao_com_conta_de_outro_dono_e_recusado(dono, conta_factory):
    alheia = conta_factory()
    with pytest.raises(servicos.ErroDePredefinicao):
        servicos.criar_padrao(dono, alheia, conta_factory(dono=dono))


def test_etapas_validas_nao_dao_erro(dono, conta_factory):
    assert servicos.validar_etapas(dono, _etapas(dono, conta_factory(dono=dono))) == []


def test_implementar_sem_conta_da_erro(dono, conta_factory):
    etapas = _etapas(
        dono,
        conta_factory(dono=dono),
        implementar={"papel": {"tipo": "humano"}, "gatilho": "webhook"},
    )
    erros = servicos.validar_etapas(dono, etapas)
    assert any("implementar" in e and "conta" in e for e in erros)


def test_conta_de_outro_dono_da_erro(dono, conta_factory):
    alheia = conta_factory(dono=Dono.objects.create(nome="Outro"))
    erros = servicos.validar_etapas(dono, _etapas(dono, alheia))
    assert erros
    assert any("não encontrada" in e or "não é sua" in e for e in erros)


def test_promover_exige_humano(dono, conta_factory):
    etapas = _etapas(
        dono,
        conta_factory(dono=dono),
        promover={"papel": {"tipo": "central"}, "gatilho": "webhook"},
    )
    assert any("promover" in e and "humano" in e for e in servicos.validar_etapas(dono, etapas))


def test_publicar_tasks_e_merge_exigem_central(dono, conta_factory):
    etapas = _etapas(
        dono,
        conta_factory(dono=dono),
        merge={"papel": {"tipo": "humano"}, "gatilho": "webhook"},
    )
    assert any("merge" in e and "central" in e for e in servicos.validar_etapas(dono, etapas))


def test_temporizador_sem_minutos_da_erro(dono, conta_factory):
    conta = conta_factory(dono=dono)
    sem = _etapas(dono, conta, merge={"papel": {"tipo": "central"}, "gatilho": "temporizador"})
    assert any("temporizador" in e for e in servicos.validar_etapas(dono, sem))
    zero = _etapas(
        dono,
        conta,
        merge={"papel": {"tipo": "central"}, "gatilho": "temporizador", "temporizador_minutos": 0},
    )
    assert servicos.validar_etapas(dono, zero)
    ok = _etapas(
        dono,
        conta,
        merge={"papel": {"tipo": "central"}, "gatilho": "temporizador", "temporizador_minutos": 5},
    )
    assert servicos.validar_etapas(dono, ok) == []


def test_chave_desconhecida_e_repetida_e_gatilho_desconhecido(dono, conta_factory):
    etapas = _etapas(dono, conta_factory(dono=dono))
    etapas.append({"chave": "voar", "papel": {"tipo": "central"}, "gatilho": "webhook"})
    etapas.append(dict(etapas[0]))
    etapas[1] = {**etapas[1], "gatilho": "nunca"}
    texto = " ".join(servicos.validar_etapas(dono, etapas))
    assert "voar" in texto and "repetida" in texto and "nunca" in texto


def test_metodo_desconhecido_da_erro(dono, conta_factory):
    erros = servicos.validar_predefinicao(dono, "spec-kit", _etapas(dono, conta_factory(dono=dono)))
    assert erros == ["Método desconhecido: spec-kit."]


def test_modelo_e_opcional_e_fica_gravado(dono, conta_factory):
    conta = conta_factory(dono=dono)
    com_modelo = _etapas(
        dono,
        conta,
        implementar={
            "papel": {"tipo": "conta", "conta_id": str(conta.id), "modelo": "claude-opus"},
            "gatilho": "anterior_concluida",
        },
    )
    assert servicos.validar_etapas(dono, com_modelo) == []
    p = servicos.criar_predefinicao(
        dono, nome="X", descricao="", metodo="superpowers", etapas=com_modelo
    )
    p.refresh_from_db()
    assert p.etapas[1]["papel"]["modelo"] == "claude-opus"

    longo = _etapas(
        dono,
        conta,
        implementar={
            "papel": {"tipo": "conta", "conta_id": str(conta.id), "modelo": "m" * 65},
            "gatilho": "anterior_concluida",
        },
    )
    assert servicos.validar_etapas(dono, longo)
    numero = _etapas(
        dono,
        conta,
        implementar={
            "papel": {"tipo": "conta", "conta_id": str(conta.id), "modelo": 3},
            "gatilho": "anterior_concluida",
        },
    )
    assert servicos.validar_etapas(dono, numero)


@pytest.mark.parametrize(
    "etapas",
    [
        None,
        "texto",
        {"a": 1},
        [1],
        [None],
        [{}],
        [{"chave": 1}],
        [{"chave": ["x"], "papel": {}, "gatilho": "webhook"}],
        [{"chave": "merge"}],
        [{"chave": "merge", "papel": "central", "gatilho": "webhook"}],
        [{"chave": "merge", "papel": {}, "gatilho": "webhook"}],
        [{"chave": "merge", "papel": {"tipo": "central"}, "gatilho": ["webhook"]}],
        [{"chave": "implementar", "papel": {"tipo": "conta"}, "gatilho": "webhook"}],
        [{"chave": "implementar", "papel": {"tipo": "conta", "conta_id": 5}, "gatilho": "webhook"}],
        [
            {
                "chave": "implementar",
                "papel": {"tipo": "conta", "conta_id": "xx"},
                "gatilho": "webhook",
            }
        ],
        [
            {
                "chave": "merge",
                "papel": {"tipo": "central"},
                "gatilho": "temporizador",
                "temporizador_minutos": True,
            }
        ],
        [
            {
                "chave": "merge",
                "papel": {"tipo": "central"},
                "gatilho": "temporizador",
                "temporizador_minutos": "5",
            }
        ],
        [
            {
                "chave": "merge",
                "papel": {"tipo": "central"},
                "gatilho": "webhook",
                "temporizador_minutos": 1.5,
            }
        ],
    ],
)
def test_formatos_invalidos_dao_erro_e_nao_excecao(dono, etapas):
    erros = servicos.validar_etapas(dono, etapas)
    assert erros
    assert all(isinstance(e, str) for e in erros)


def test_duplicar_copia_etapas(dono, conta_factory):
    original = servicos.criar_padrao(dono, conta_factory(dono=dono), conta_factory(dono=dono))
    copia = servicos.duplicar(original, "Cópia")

    assert copia.pk != original.pk
    assert copia.nome == "Cópia"
    assert copia.etapas == original.etapas
    assert copia.etapas is not original.etapas
    assert copia.dono_id == original.dono_id
    assert copia.merge_autonomo == original.merge_autonomo


# projetos.servicos.validar_contas_do_projeto


def test_conta_de_cliente_y_em_projeto_do_cliente_x_e_recusada(
    dono, conta_factory, cliente_x, cliente_y
):
    conta = conta_factory(dono=dono, cliente=cliente_y, nome="Conta do Y")
    pred = servicos.criar_padrao(dono, conta, conta_factory(dono=dono))
    projeto = Projeto(dono=dono, cliente=cliente_x)

    assert projetos_servicos.validar_contas_do_projeto(projeto, pred) == [
        "A conta Conta do Y é do cliente Y e não pode trabalhar neste projeto."
    ]


def test_conta_do_dono_vale_em_projeto_de_cliente(dono, conta_factory, cliente_x):
    pred = servicos.criar_padrao(dono, conta_factory(dono=dono), conta_factory(dono=dono))
    assert (
        projetos_servicos.validar_contas_do_projeto(Projeto(dono=dono, cliente=cliente_x), pred)
        == []
    )


def test_conta_do_cliente_x_vale_no_projeto_do_cliente_x(dono, conta_factory, cliente_x):
    conta = conta_factory(dono=dono, cliente=cliente_x)
    pred = servicos.criar_padrao(dono, conta, conta)
    assert (
        projetos_servicos.validar_contas_do_projeto(Projeto(dono=dono, cliente=cliente_x), pred)
        == []
    )


def test_sem_predefinicao_nao_ha_erro(dono):
    assert projetos_servicos.validar_contas_do_projeto(Projeto(dono=dono), None) == []


# normalização, ordem e obrigatoriedade


def test_etapas_na_ordem_errada_dao_erro(dono, conta_factory):
    etapas = list(reversed(_etapas(dono, conta_factory(dono=dono))))
    erros = servicos.validar_etapas(dono, etapas)
    assert (
        "As etapas precisam seguir a ordem: publicar_tasks, implementar, revisar, merge, promover."
        in erros
    )


def test_subconjunto_na_ordem_e_aceito(dono, conta_factory):
    etapas = [e for e in _etapas(dono, conta_factory(dono=dono)) if e["chave"] != "promover"]
    assert servicos.validar_etapas(dono, etapas) == []


def test_implementar_e_obrigatoria(dono, conta_factory):
    etapas = [e for e in _etapas(dono, conta_factory(dono=dono)) if e["chave"] != "implementar"]
    assert "A etapa implementar é obrigatória." in servicos.validar_etapas(dono, etapas)
    assert "A etapa implementar é obrigatória." in servicos.validar_etapas(dono, [])


def test_normalizacao_descarta_campos_desconhecidos(dono, conta_factory):
    conta = conta_factory(dono=dono)
    etapas = _etapas(dono, conta)
    etapas[0] = {**etapas[0], "extra": 1, "papel": {"tipo": "central", "conta_id": str(conta.id)}}
    etapas[1]["papel"] = {
        "tipo": "conta",
        "conta_id": str(conta.id).upper(),
        "modelo": "  m1  ",
        "lixo": True,
    }
    etapas[2]["papel"]["modelo"] = "   "
    etapas[3] = {**etapas[3], "temporizador_minutos": 7}
    assert servicos.validar_etapas(dono, etapas) == []

    p = servicos.criar_predefinicao(dono, nome="N", etapas=etapas)
    p.refresh_from_db()
    por = {e["chave"]: e for e in p.etapas}
    assert por["publicar_tasks"] == {
        "chave": "publicar_tasks",
        "papel": {"tipo": "central"},
        "gatilho": "anterior_concluida",
    }
    assert por["implementar"]["papel"] == {
        "tipo": "conta",
        "conta_id": str(conta.id),
        "modelo": "m1",
    }
    assert "modelo" not in por["revisar"]["papel"]
    assert "temporizador_minutos" not in por["merge"]


def test_normalizacao_mantem_temporizador(dono, conta_factory):
    etapas = _etapas(
        dono,
        conta_factory(dono=dono),
        merge={"papel": {"tipo": "central"}, "gatilho": "temporizador", "temporizador_minutos": 3},
    )
    p = servicos.criar_predefinicao(dono, nome="N", etapas=etapas)
    assert {e["chave"]: e for e in p.etapas}["merge"]["temporizador_minutos"] == 3


def test_duplicar_normaliza(dono, conta_factory):
    original = servicos.criar_padrao(dono, conta_factory(dono=dono), conta_factory(dono=dono))
    original.etapas[0]["lixo"] = 1
    copia = servicos.duplicar(original, "C")
    assert "lixo" not in copia.etapas[0]


def test_projetos_registra_o_verificador_na_inicializacao():
    assert projetos_servicos.validar_projetos_da_predefinicao in servicos._verificadores_de_uso


def test_sem_verificador_e_com_usos_o_patch_falha_sem_gravar(dono, conta_factory, monkeypatch):
    pred = servicos.criar_padrao(dono, conta_factory(dono=dono), conta_factory(dono=dono))
    Projeto.objects.create(
        dono=dono,
        nome="P",
        conexao=_conexao(dono),
        repositorio_caminho="a/b",
        repositorio_id_externo="1",
        repositorio_url="u",
        predefinicao=pred,
    )
    monkeypatch.setattr(servicos, "_verificadores_de_uso", [])
    with pytest.raises(servicos.ErroDePredefinicao):
        servicos.atualizar_predefinicao(pred, {"nome": "Outro"})
    pred.refresh_from_db()
    assert pred.nome == "Padrão"


def _conexao(dono):
    from apps.plataformas.models import ConexaoPlataforma

    return ConexaoPlataforma.objects.create(
        dono=dono, nome="GL", tipo="gitlab", url_base="https://g.exemplo.com"
    )
