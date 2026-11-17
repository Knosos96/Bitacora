import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import requiere_rol, usuario_actual
from app.enums import Rol
from app.models import Area, Usuario
from app.schemas import AreaIn, AreaOut, AreaPatch

router = APIRouter(prefix="/areas", tags=["areas"])


@router.get("", response_model=list[AreaOut])
def listar_areas(
    incluir_inactivas: bool = Query(False, description="Solo encargado y jefe"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    consulta = select(Area).order_by(Area.nombre)
    if not (incluir_inactivas and usuario.rol in (Rol.encargado, Rol.jefe)):
        consulta = consulta.where(Area.activa)
    return db.scalars(consulta).all()


@router.post("", response_model=AreaOut, status_code=201)
def crear_area(
    datos: AreaIn,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.jefe, Rol.encargado)),
):
    nombre = datos.nombre.strip()
    if db.scalar(select(Area).where(Area.nombre == nombre)):
        raise HTTPException(400, "Esa área ya existe")
    area = Area(nombre=nombre)
    db.add(area)
    db.commit()
    return area


@router.patch("/{area_id}", response_model=AreaOut)
def modificar_area(
    area_id: uuid.UUID,
    datos: AreaPatch,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.jefe, Rol.encargado)),
):
    """CU-17. Renombrar, desactivar o reactivar. Desactivar no toca los eventos ya registrados."""
    area = db.get(Area, area_id)
    if area is None:
        raise HTTPException(404, "Área no encontrada")
    if datos.nombre is not None:
        nombre = datos.nombre.strip()
        otra = db.scalar(select(Area).where(Area.nombre == nombre, Area.id != area.id))
        if otra:
            raise HTTPException(400, "Esa área ya existe")
        area.nombre = nombre
    if datos.activa is not None:
        area.activa = datos.activa
    db.commit()
    return area
