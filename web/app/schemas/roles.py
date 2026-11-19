"""Esquemas de roles personalizados."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import Permiso


class RolPersonalizadoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: str | None = None
    permisos: list[Permiso] = Field(default_factory=list)


class RolPersonalizadoPatch(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    descripcion: str | None = None
    permisos: list[Permiso] | None = None
    activo: bool | None = None


class RolPersonalizadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    descripcion: str
    permisos: list[str]
    activo: bool
    creado_en: datetime
