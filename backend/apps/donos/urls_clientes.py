from rest_framework.routers import DefaultRouter

from .views import ClienteViewSet

router = DefaultRouter(trailing_slash=True)
router.include_root_view = False
router.register("", ClienteViewSet, basename="cliente")

urlpatterns = router.urls
