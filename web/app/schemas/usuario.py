"""Esquemas de usuario."""
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.enums import Rol
from app.schemas.common import validar_clave_segura, validar_no_blanco


class UsuarioIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    correo: EmailStr
    clave: str = Field(min_length=8, max_length=72)
    rol: Rol
    rol_custom_id: uuid.UUID | None = None

    @field_validator("nombre")
    @classmethod
    def _nombre_valido(cls, v: str) -> str:
        return validar_no_blanco(v)

    @field_validator("clave")
    @classmethod
    def _clave_valida(cls, v: str) -> str:
        return validar_clave_segura(v)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    correo: str
    rol: Rol
    activo: bool
    rol_custom_id: uuid.UUID | None = None
    rol_custom_nombre: str | None = None
    permisos: list[str] = Field(default_factory=list)


class UsuarioRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str


class UsuarioPatch(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    rol: Rol | None = None
    activo: bool | None = None
    clave: str | None = Field(default=None, min_length=8, max_length=72)

    @field_validator("nombre")
    @classmethod
    def _nombre_valido(cls, v: str | None) -> str | None:
        return validar_no_blanco(v)

    @field_validator("clave")
    @classmethod
    def _clave_valida(cls, v: str | None) -> str | None:
        return validar_clave_segura(v)
