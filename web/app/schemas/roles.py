"""Esquemas de roles personalizados."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import Permiso
from app.schemas.common import validar_no_blanco


class RolPersonalizadoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=200)
    permisos: list[Permiso] = Field(default_factory=list)

    @field_validator("nombre")
    @classmethod
    def _nombre_valido(cls, v: str) -> str:
        return validar_no_blanco(v)


class RolPersonalizadoPatch(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=200)
    permisos: list[Permiso] | None = None
    activo: bool | None = None

    @field_validator("nombre")
    @classmethod
    def _nombre_valido(cls, v: str | None) -> str | None:
        return validar_no_blanco(v)


class RolPersonalizadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    descripcion: str
    permisos: list[str]
    activo: bool
    creado_en: datetime
