from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from apps.plataformas import webhooks

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/webhooks/github/", webhooks.github),
    path("api/webhooks/gitlab/<uuid:conexao_id>/", webhooks.gitlab),
    path("api/clientes/", include("apps.donos.urls_clientes")),
    path("api/", include("apps.agentes.urls")),
    path("api/", include("apps.fluxos.urls")),
    path("api/", include("apps.plataformas.urls")),
    path("api/", include("apps.projetos.urls")),
    path("api/sessao/", include("apps.donos.urls")),
    path("api/saude/", include("apps.saude.urls")),
]
