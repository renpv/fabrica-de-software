from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ConexaoPlataformaViewSet,
    InstaladoGitHubView,
    ManifestoGitHubView,
    RetornoGitHubView,
)

router = DefaultRouter()
router.include_root_view = False
router.register("conexoes-plataforma", ConexaoPlataformaViewSet, basename="conexao-plataforma")

urlpatterns = [
    path("conexoes-plataforma/github/manifesto/", ManifestoGitHubView.as_view()),
    path("conexoes-plataforma/github/retorno/", RetornoGitHubView.as_view()),
    path("conexoes-plataforma/github/instalado/", InstaladoGitHubView.as_view()),
    *router.urls,
]
