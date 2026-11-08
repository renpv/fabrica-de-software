from tests.apoio.models import Anotacao
from tests.apoio.views import AnotacaoViewSet


def _com_dono(rf_request, membro):
    """Simula o DonoMiddleware sobre uma requisição de teste."""
    from apps.donos.middleware import DonoMiddleware

    rf_request.user = membro.usuario
    rf_request._dont_enforce_csrf_checks = True  # o RequestFactory não faz isso sozinho
    DonoMiddleware(lambda r: None)(rf_request)
    return rf_request


def test_mixin_nao_cruza_donos(rf, membro_factory):
    a, b = membro_factory(), membro_factory()
    do_a = Anotacao.objects.create(dono=a.dono, texto="de A")
    do_b = Anotacao.objects.create(dono=b.dono, texto="de B")

    req = _com_dono(rf.get("/anotacoes/"), a)
    resposta = AnotacaoViewSet.as_view({"get": "list"})(req)
    assert [i["texto"] for i in resposta.data] == ["de A"]

    req = _com_dono(rf.get(f"/anotacoes/{do_b.id}/"), a)
    assert AnotacaoViewSet.as_view({"get": "retrieve"})(req, pk=do_b.id).status_code == 404
    req = _com_dono(rf.get(f"/anotacoes/{do_a.id}/"), a)
    assert AnotacaoViewSet.as_view({"get": "retrieve"})(req, pk=do_a.id).status_code == 200


def test_criar_grava_o_dono_da_requisicao(rf, membro_factory):
    a = membro_factory()
    req = _com_dono(rf.post("/anotacoes/", {"texto": "nova"}, content_type="application/json"), a)
    resposta = AnotacaoViewSet.as_view({"post": "create"})(req)
    assert resposta.status_code == 201
    assert Anotacao.objects.get(texto="nova").dono == a.dono


def test_sem_dono_a_lista_vem_vazia(rf, membro_factory, django_user_model):
    a = membro_factory()
    Anotacao.objects.create(dono=a.dono, texto="de A")
    solto = django_user_model.objects.create_user(username="solto", password="x")
    req = rf.get("/anotacoes/")
    req.user = solto
    from apps.donos.middleware import DonoMiddleware

    DonoMiddleware(lambda r: None)(req)
    assert req.dono is None
    assert AnotacaoViewSet.as_view({"get": "list"})(req).data == []


def test_do_dono_filtra_pelo_dono(membro_factory):
    a, b = membro_factory(), membro_factory()
    Anotacao.objects.create(dono=a.dono, texto="de A")
    Anotacao.objects.create(dono=b.dono, texto="de B")
    assert [x.texto for x in Anotacao.objects.do_dono(a.dono)] == ["de A"]


def test_middleware_anonimo_deixa_dono_none(rf, db):
    from django.contrib.auth.models import AnonymousUser

    req = rf.get("/")
    req.user = AnonymousUser()
    from apps.donos.middleware import DonoMiddleware

    DonoMiddleware(lambda r: None)(req)
    assert req.dono is None
