from . import servicos


class DonoMiddleware:
    """Define `request.dono` a partir do usuário logado (None sem login ou sem Membro).

    Deve ficar depois do AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.dono = servicos.dono_do_usuario(request.user)
        return self.get_response(request)
