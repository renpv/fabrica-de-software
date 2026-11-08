from rest_framework.permissions import BasePermission


class TemDono(BasePermission):
    """Exige que o usuário logado esteja ligado a um dono (tenha Membro)."""

    message = (
        "Este usuário não está ligado a nenhum dono. "
        "Peça para criar o acesso com manage.py criar_dono."
    )

    def has_permission(self, request, view):
        return getattr(request, "dono", None) is not None
