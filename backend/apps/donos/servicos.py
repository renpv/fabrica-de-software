"""Regras de negócio de donos e de login. Views e comandos só chamam este módulo."""

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Dono, Membro


def dono_do_usuario(usuario) -> Dono | None:
    """O dono do usuário, ou None se ele for anônimo ou não tiver Membro."""
    if not usuario.is_authenticated:
        return None
    membro = Membro.objects.select_related("dono").filter(usuario=usuario).first()
    return membro.dono if membro else None


def autenticar(request, usuario: str, senha: str) -> Membro | None:
    """Confere usuário e senha e abre a sessão. None se errado ou sem dono."""
    user = authenticate(request, username=usuario, password=senha)
    if user is None:
        return None
    membro = Membro.objects.select_related("dono", "usuario").filter(usuario=user).first()
    if membro is None:
        return None
    login(request, user)
    return membro


def criar_dono(nome: str, usuario: str, email: str, senha: str) -> Membro:
    """Cria usuário, dono e vínculo. ValueError se o usuário já existe ou a senha é fraca."""
    modelo = get_user_model()
    if modelo.objects.filter(username=usuario).exists():
        raise ValueError(f'O usuário "{usuario}" já existe. Escolha outro nome de usuário.')
    try:
        validate_password(senha, modelo(username=usuario, email=email))
    except ValidationError as erro:
        raise ValueError(" ".join(erro.messages)) from erro
    with transaction.atomic():
        user = modelo.objects.create_user(username=usuario, email=email, password=senha)
        dono = Dono.objects.create(nome=nome)
        return Membro.objects.create(usuario=user, dono=dono)


def encerrar(request) -> None:
    """Encerra a sessão do usuário."""
    logout(request)
