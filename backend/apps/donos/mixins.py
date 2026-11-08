from rest_framework.exceptions import PermissionDenied


class EscopoDoDonoMixin:
    """Mixin de ViewSet/GenericAPIView: só enxerga e só grava registros do dono da requisição."""

    def get_queryset(self):
        consulta = super().get_queryset()
        dono = getattr(self.request, "dono", None)
        if dono is None:
            return consulta.none()
        return consulta.filter(dono=dono)

    def perform_create(self, serializer):
        dono = getattr(self.request, "dono", None)
        if dono is None:
            raise PermissionDenied(
                "Sua conta não pertence a nenhum dono. Fale com o administrador."
            )
        serializer.save(dono=dono)
