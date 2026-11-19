"""Funciones de áreas."""
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Rol
from app.models import Area, Usuario
from app.schemas import AreaIn, AreaPatch


def listar(db: Session, usuario: Usuario, incluir_inactivas: bool = False) -> list[Area]:
    consulta = select(Area).order_by(Area.nombre)
    if not (incluir_inactivas and usuario.rol in (Rol.encargado, Rol.jefe)):
        consulta = consulta.where(Area.activa)
    return list(db.scalars(consulta).all())


def crear(db: Session, datos: AreaIn) -> Area:
    nombre = datos.nombre.strip()
    if db.scalar(select(Area).where(Area.nombre == nombre)):
        raise HTTPException(400, "Esa área ya existe")
    area = Area(nombre=nombre)
    db.add(area)
    db.commit()
    return area


def modificar(db: Session, area_id: uuid.UUID, datos: AreaPatch) -> Area:
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
