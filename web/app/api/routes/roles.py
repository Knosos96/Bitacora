"""Rutas de roles personalizados."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import requiere_rol
from app.core.enums import Rol
from app.models import Usuario
from app.schemas import RolPersonalizadoIn, RolPersonalizadoOut, RolPersonalizadoPatch
from app.services import roles as svc

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RolPersonalizadoOut])
def listar_roles(incluir_inactivos: bool = False, db: Session = Depends(get_db), _: Usuario = Depends(requiere_rol(Rol.jefe, Rol.encargado))):
    return svc.listar(db, incluir_inactivos)


@router.get("/permisos", response_model=list[dict])
def listar_permisos(_: Usuario = Depends(requiere_rol(Rol.jefe))):
    return svc.listar_permisos()


@router.post("", response_model=RolPersonalizadoOut, status_code=201)
def crear_rol(datos: RolPersonalizadoIn, db: Session = Depends(get_db), jefe: Usuario = Depends(requiere_rol(Rol.jefe))):
    return svc.crear(db, datos, jefe)


@router.patch("/{rol_id}", response_model=RolPersonalizadoOut)
def editar_rol(rol_id: uuid.UUID, datos: RolPersonalizadoPatch, db: Session = Depends(get_db), _: Usuario = Depends(requiere_rol(Rol.jefe))):
    return svc.editar(db, rol_id, datos)


@router.delete("/{rol_id}", status_code=204)
def eliminar_rol(rol_id: uuid.UUID, db: Session = Depends(get_db), _: Usuario = Depends(requiere_rol(Rol.jefe))):
    svc.eliminar(db, rol_id)


@router.post("/asignar", response_model=dict)
def asignar_rol(usuario_id: uuid.UUID, rol_id: uuid.UUID | None = None, db: Session = Depends(get_db), _: Usuario = Depends(requiere_rol(Rol.jefe))):
    return svc.asignar(db, usuario_id, rol_id)
