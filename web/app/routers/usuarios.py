"""Rutas de usuarios."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import requiere_permiso
from app.core.enums import Permiso
from app.models import Usuario
from app.schemas import UsuarioIn, UsuarioOut, UsuarioPatch
from app.services import usuarios as svc

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.post("", response_model=UsuarioOut, status_code=201)
def crear_usuario(
    datos: UsuarioIn,
    db: Session = Depends(get_db),
    jefe: Usuario = Depends(requiere_permiso(Permiso.crear_usuarios)),
):
    return svc.crear(db, datos, actor=jefe)


@router.get("", response_model=list[UsuarioOut])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_permiso(Permiso.ver_usuarios, Permiso.crear_usuarios, Permiso.editar_usuarios)),
):
    return svc.listar(db)


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def modificar_usuario(
    usuario_id: uuid.UUID,
    datos: UsuarioPatch,
    db: Session = Depends(get_db),
    jefe: Usuario = Depends(requiere_permiso(Permiso.editar_usuarios)),
):
    return svc.modificar(db, usuario_id, datos, jefe)


@router.delete("/{usuario_id}", status_code=204)
def eliminar_usuario(
    usuario_id: uuid.UUID,
    db: Session = Depends(get_db),
    jefe: Usuario = Depends(requiere_permiso(Permiso.editar_usuarios)),
):
    svc.eliminar(db, usuario_id, jefe)
