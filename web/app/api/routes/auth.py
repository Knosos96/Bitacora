"""Rutas de autenticación."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import usuario_actual
from app.models import Usuario
from app.schemas import LoginIn, TokenOut, UsuarioOut
from app.services import auth as svc

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, db: Session = Depends(get_db)):
    return svc.login(db, datos.correo, datos.clave)


@router.get("/yo", response_model=UsuarioOut)
def yo(u: Usuario = Depends(usuario_actual)):
    return u
