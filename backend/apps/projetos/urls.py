from rest_framework.routers import DefaultRouter

from .views import ProjetoViewSet

router = DefaultRouter()
router.include_root_view = False
router.register("projetos", ProjetoViewSet, basename="projeto")

urlpatterns = router.urls
