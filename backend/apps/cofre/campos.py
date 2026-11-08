"""Campo de modelo que guarda JSON cifrado. O Python vê um dict; o banco, só o texto cifrado."""

import json

from django.db import models

from . import servicos


class ValorSecreto(dict):
    """Dict que não se mostra: repr e str não vazam o conteúdo em log nem em erro."""

    def __repr__(self) -> str:
        return "<segredo>"

    __str__ = __repr__


class CampoSecretoJSON(models.TextField):
    """Não serve para filtrar por valor: o texto cifrado muda a cada gravação."""

    description = "JSON cifrado pelo cofre"

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        return ValorSecreto(json.loads(servicos.decifrar(value)))

    def to_python(self, value):
        if value is None or isinstance(value, ValorSecreto):
            return value
        if isinstance(value, dict):
            return ValorSecreto(value)
        if isinstance(value, str):
            return ValorSecreto(json.loads(value))
        return value

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        return servicos.cifrar(json.dumps(dict(value), ensure_ascii=False))
