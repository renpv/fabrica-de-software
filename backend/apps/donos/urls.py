from django.urls import path

from .views import SessaoView

urlpatterns = [path("", SessaoView.as_view(), name="sessao")]
