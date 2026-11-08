from drf_spectacular.authentication import SessionScheme


class SessaoAutenticacaoScheme(SessionScheme):
    """Documenta `SessaoAutenticacao` no OpenAPI como o cookie de sessão do Django."""

    target_class = "apps.donos.views.SessaoAutenticacao"
