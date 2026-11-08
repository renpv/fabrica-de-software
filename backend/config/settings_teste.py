"""Configurações dos testes: as de produção mais o app de apoio `tests.apoio`."""

from .settings import *  # noqa: F403
from .settings import INSTALLED_APPS

INSTALLED_APPS = [*INSTALLED_APPS, "tests.apoio"]
