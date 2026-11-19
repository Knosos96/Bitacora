"""Funciones de autenticación."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import HTTPException

from app.core.security import crear_token, verificar_clave
from app.models import Usuario
from app.schemas import TokenOut, UsuarioOut


def login(db: Session, correo: str, clave: str) -> TokenOut:
    u = db.scalar(select(Usuario).where(Usuario.correo == correo.lower()))
    if u is None or not u.activo or not verificar_clave(clave, u.clave_hash):
        raise HTTPException(401, "Correo o clave incorrectos")
    return TokenOut(token=crear_token(str(u.id)), usuario=UsuarioOut.model_validate(u))
