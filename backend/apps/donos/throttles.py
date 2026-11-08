import hashlib

from rest_framework.throttling import SimpleRateThrottle


class LoginPorUsuarioThrottle(SimpleRateThrottle):
    """Limita as tentativas de login por nome de usuário, de qualquer IP."""

    scope = "sessao_usuario"

    def get_cache_key(self, request, view):
        dados = request.data
        usuario = dados.get("usuario") if hasattr(dados, "get") else None
        if not isinstance(usuario, str) or not usuario.strip():
            return None
        ident = hashlib.sha256(usuario.strip().lower().encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}
