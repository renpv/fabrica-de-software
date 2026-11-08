from django.apps import AppConfig


class DonosConfig(AppConfig):
    name = "apps.donos"
    label = "donos"

    def ready(self):
        from . import schema  # noqa: F401  (registra a extensão do OpenAPI)
