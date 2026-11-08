from django.apps import AppConfig


class CofreConfig(AppConfig):
    name = "apps.cofre"
    label = "cofre"

    def ready(self):
        from . import servicos

        servicos.verificar_configuracao()
