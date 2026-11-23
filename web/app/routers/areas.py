"""Rutas de áreas."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import requiere_permiso, usuario_actual
from app.core.enums import Permiso
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
    actor: Usuario = Depends(requiere_permiso(Permiso.gestionar_areas)),
):
    return svc.crear(db, datos, actor=actor)


@router.patch("/{area_id}", response_model=AreaOut)
def modificar_area(
    area_id: uuid.UUID,
    datos: AreaPatch,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(requiere_permiso(Permiso.gestionar_areas)),
):
    return svc.modificar(db, area_id, datos, actor=actor)


@router.delete("/{area_id}", status_code=204)
def eliminar_area(
    area_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(requiere_permiso(Permiso.gestionar_areas)),
):
    svc.eliminar(db, area_id, actor=actor)
