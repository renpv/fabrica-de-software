from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ContaAgenteViewSet, TiposDeAgenteView

router = DefaultRouter()
router.include_root_view = False
router.register("contas-agente", ContaAgenteViewSet, basename="conta-agente")

urlpatterns = [
    path("tipos-de-agente/", TiposDeAgenteView.as_view(), name="tipos-de-agente"),
    *router.urls,
]
