"""Rutas de claves API."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import requiere_permiso
from app.core.enums import Permiso
from app.models import Usuario
from app.schemas import ClaveApiCreada, ClaveApiIn, ClaveApiOut
from app.services import claves as svc

router = APIRouter(prefix="/claves-api", tags=["claves-api"])


@router.post("", response_model=ClaveApiCreada, status_code=201)
def crear_clave(
    datos: ClaveApiIn,
    db: Session = Depends(get_db),
    jefe: Usuario = Depends(requiere_permiso(Permiso.gestionar_claves_api)),
):
    return svc.crear(db, datos, jefe)


@router.get("", response_model=list[ClaveApiOut])
def listar_claves(
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_permiso(Permiso.gestionar_claves_api)),
):
    return svc.listar(db)


@router.delete("/{clave_id}", response_model=ClaveApiOut)
def revocar_clave(
    clave_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(requiere_permiso(Permiso.gestionar_claves_api)),
):
    return svc.revocar(db, clave_id, actor=actor)


@router.delete("/{clave_id}/permanente", status_code=204)
def eliminar_clave(
    clave_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(requiere_permiso(Permiso.gestionar_claves_api)),
):
    svc.eliminar(db, clave_id, actor=actor)
