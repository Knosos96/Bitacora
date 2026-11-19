"""Esquemas de subtipos."""
from pydantic import BaseModel, Field

from app.core.enums import Tipo


class SubtipoIn(BaseModel):
    tipo: Tipo
    nombre: str = Field(pattern="^[a-z0-9_]{2,40}$")


class SubtipoPatch(BaseModel):
    activo: bool


class SubtipoOut(BaseModel):
    tipo: Tipo
    nombre: str
    activo: bool
    base: bool
