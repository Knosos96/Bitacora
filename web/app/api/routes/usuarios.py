"""Rutas de usuarios."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import requiere_rol
from app.core.enums import Rol
from app.models import Usuario
from app.schemas import UsuarioIn, UsuarioOut, UsuarioPatch
from app.services import usuarios as svc

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.post("", response_model=UsuarioOut, status_code=201)
def crear_usuario(datos: UsuarioIn, db: Session = Depends(get_db), _: Usuario = Depends(requiere_rol(Rol.jefe))):
    return svc.crear(db, datos)


@router.get("", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db), _: Usuario = Depends(requiere_rol(Rol.jefe, Rol.encargado))):
    return svc.listar(db)


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def modificar_usuario(
    usuario_id: uuid.UUID,
    datos: UsuarioPatch,
    db: Session = Depends(get_db),
    jefe: Usuario = Depends(requiere_rol(Rol.jefe)),
):
    return svc.modificar(db, usuario_id, datos, jefe)
