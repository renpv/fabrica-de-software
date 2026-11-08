from django.urls import path

from .views import SaudeView

urlpatterns = [path("", SaudeView.as_view(), name="saude")]
