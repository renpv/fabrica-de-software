from django.apps import AppConfig


class ProjetosConfig(AppConfig):
    name = "apps.projetos"
    label = "projetos"

    def ready(self):
        from apps.fluxos.servicos import registrar_verificador_de_uso

        from .servicos import validar_projetos_da_predefinicao

        registrar_verificador_de_uso(validar_projetos_da_predefinicao)
