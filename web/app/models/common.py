"""Utilidades compartidas de modelos ORM."""
from datetime import datetime, timezone

from sqlalchemy import Enum


def enum_col(e, nombre):
    """Guarda el valor ("en_proceso") y no el nombre Python."""
    return Enum(e, name=nombre, values_callable=lambda x: [m.value for m in x])


def ahora():
    return datetime.now(timezone.utc)


# aliases usados en el resto del código
_enum = enum_col
_ahora = ahora
