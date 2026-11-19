"""Esquemas de autenticación."""
from pydantic import BaseModel, EmailStr

from app.schemas.usuario import UsuarioOut


class LoginIn(BaseModel):
    correo: EmailStr
    clave: str


class TokenOut(BaseModel):
    token: str
    tipo: str = "bearer"
    usuario: UsuarioOut
