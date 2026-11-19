"""Esquemas de usuario."""
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import Rol


class UsuarioIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    correo: EmailStr
    clave: str = Field(min_length=8)
    rol: Rol


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    correo: str
    rol: Rol
    activo: bool
    rol_custom_id: uuid.UUID | None = None
    rol_custom_nombre: str | None = None


class UsuarioRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str


class UsuarioPatch(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    rol: Rol | None = None
    activo: bool | None = None
    clave: str | None = Field(default=None, min_length=8)
