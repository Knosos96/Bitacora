"""Rutas de subtipos."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import requiere_rol, usuario_actual
from app.core.enums import Rol, Tipo
from app.models import Usuario
from app.schemas import SubtipoIn, SubtipoOut, SubtipoPatch
from app.services import subtipos as svc

router = APIRouter(prefix="/subtipos", tags=["subtipos"])


@router.get("", response_model=list[SubtipoOut])
def listar_subtipos(
    tipo: Tipo | None = None,
    incluir_inactivos: bool = Query(False),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    return svc.listar(db, usuario, tipo, incluir_inactivos)


@router.post("", response_model=SubtipoOut, status_code=201)
def crear_subtipo(datos: SubtipoIn, db: Session = Depends(get_db), _: Usuario = Depends(requiere_rol(Rol.encargado, Rol.jefe))):
    return svc.crear(db, datos)


@router.patch("/{tipo}/{nombre}", response_model=SubtipoOut)
def activar_o_desactivar(
    tipo: Tipo, nombre: str, datos: SubtipoPatch,
    db: Session = Depends(get_db), _: Usuario = Depends(requiere_rol(Rol.encargado, Rol.jefe)),
):
    return svc.activar(db, tipo, nombre, datos)
