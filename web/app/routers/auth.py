"""Rutas de autenticación."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import usuario_actual
from app.models import Usuario
from app.schemas import LoginIn, TokenOut, UsuarioOut
from app.services import auth as svc
from app.services.usuarios import a_salida

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "local"
    return svc.login(db, datos.correo, datos.clave, ip=ip)


@router.get("/yo", response_model=UsuarioOut)
def yo(u: Usuario = Depends(usuario_actual)):
    return a_salida(u)
