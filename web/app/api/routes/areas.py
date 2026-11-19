"""Rutas de áreas."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import requiere_rol, usuario_actual
from app.core.enums import Rol
from app.models import Usuario
from app.schemas import AreaIn, AreaOut, AreaPatch
from app.services import areas as svc

router = APIRouter(prefix="/areas", tags=["areas"])


@router.get("", response_model=list[AreaOut])
def listar_areas(
    incluir_inactivas: bool = Query(False),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    return svc.listar(db, usuario, incluir_inactivas)


@router.post("", response_model=AreaOut, status_code=201)
def crear_area(
    datos: AreaIn,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.jefe, Rol.encargado)),
):
    return svc.crear(db, datos)


@router.patch("/{area_id}", response_model=AreaOut)
def modificar_area(
    area_id: uuid.UUID,
    datos: AreaPatch,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.jefe, Rol.encargado)),
):
    return svc.modificar(db, area_id, datos)
