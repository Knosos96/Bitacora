from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import usuario_actual
from app.models import Usuario
from app.schemas import LoginIn, TokenOut, UsuarioOut
from app.security import crear_token, verificar_clave

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(Usuario).where(Usuario.correo == datos.correo.lower()))
    if u is None or not u.activo or not verificar_clave(datos.clave, u.clave_hash):
        raise HTTPException(401, "Correo o clave incorrectos")
    return TokenOut(token=crear_token(str(u.id)), usuario=UsuarioOut.model_validate(u))


@router.get("/yo", response_model=UsuarioOut)
def yo(u: Usuario = Depends(usuario_actual)):
    return u
