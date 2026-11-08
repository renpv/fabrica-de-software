from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/clientes/", include("apps.donos.urls_clientes")),
    path("api/", include("apps.agentes.urls")),
    path("api/", include("apps.fluxos.urls")),
    path("api/", include("apps.plataformas.urls")),
    path("api/", include("apps.projetos.urls")),
    path("api/sessao/", include("apps.donos.urls")),
    path("api/saude/", include("apps.saude.urls")),
]
