from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EtapasEGatilhosView, PredefinicaoViewSet

router = DefaultRouter()
router.include_root_view = False
router.register("predefinicoes", PredefinicaoViewSet, basename="predefinicao")

urlpatterns = [
    path("etapas-e-gatilhos/", EtapasEGatilhosView.as_view(), name="etapas-e-gatilhos"),
    *router.urls,
]
