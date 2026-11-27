"""Esquemas de autenticación."""
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import validar_clave_segura, validar_no_blanco
from app.schemas.usuario import UsuarioOut


class LoginIn(BaseModel):
    correo: EmailStr
    clave: str


class PerfilPatch(BaseModel):
    clave_actual: str = Field(min_length=1, max_length=72)
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    correo: EmailStr | None = None
    clave_nueva: str | None = Field(default=None, min_length=8, max_length=72)

    @field_validator("nombre")
    @classmethod
    def _nombre_valido(cls, v: str | None) -> str | None:
        return validar_no_blanco(v)

    @field_validator("clave_nueva")
    @classmethod
    def _clave_nueva_valida(cls, v: str | None) -> str | None:
        return validar_clave_segura(v)


class TokenOut(BaseModel):
    token: str
    tipo: str = "bearer"
    usuario: UsuarioOut
