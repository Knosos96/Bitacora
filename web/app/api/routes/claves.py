"""Rutas de claves API."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import requiere_rol
from app.core.enums import Rol
from app.models import Usuario
from app.schemas import ClaveApiCreada, ClaveApiIn, ClaveApiOut
from app.services import claves as svc

router = APIRouter(prefix="/claves-api", tags=["claves-api"])


@router.post("", response_model=ClaveApiCreada, status_code=201)
def crear_clave(datos: ClaveApiIn, db: Session = Depends(get_db), jefe: Usuario = Depends(requiere_rol(Rol.jefe))):
    return svc.crear(db, datos, jefe)


@router.get("", response_model=list[ClaveApiOut])
def listar_claves(db: Session = Depends(get_db), _: Usuario = Depends(requiere_rol(Rol.jefe))):
    return svc.listar(db)


@router.delete("/{clave_id}", response_model=ClaveApiOut)
def revocar_clave(clave_id: uuid.UUID, db: Session = Depends(get_db), _: Usuario = Depends(requiere_rol(Rol.jefe))):
    return svc.revocar(db, clave_id)
