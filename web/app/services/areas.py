"""Funciones de áreas."""
import uuid

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.deps import tiene_permiso
from app.core.enums import Permiso
from app.models import Area, Evento, Usuario
from app.schemas import AreaIn, AreaPatch
from app.services.historial import registrar_actividad


def listar(db: Session, usuario: Usuario, incluir_inactivas: bool = False) -> list[Area]:
    consulta = select(Area).order_by(Area.nombre)
    if not (incluir_inactivas and tiene_permiso(usuario, Permiso.gestionar_areas)):
        consulta = consulta.where(Area.activa)
    return list(db.scalars(consulta).all())


def crear(db: Session, datos: AreaIn, actor: Usuario | None = None) -> Area:
    nombre = datos.nombre.strip()
    if db.scalar(select(Area).where(Area.nombre == nombre)):
        raise HTTPException(400, "Esa área ya existe")
    area = Area(nombre=nombre)
    db.add(area)
    db.flush()
    if actor is not None:
        registrar_actividad(db, actor, "area_creada", "area", str(area.id), titulo=area.nombre)
    db.commit()
    return area


def modificar(db: Session, area_id: uuid.UUID, datos: AreaPatch, actor: Usuario | None = None) -> Area:
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
    if actor is not None:
        registrar_actividad(db, actor, "area_modificada", "area", str(area.id), titulo=area.nombre,
                            detalle=f"Activa: {area.activa}")
    db.commit()
    return area


def eliminar(db: Session, area_id: uuid.UUID, actor: Usuario | None = None) -> None:
    area = db.get(Area, area_id)
    if area is None:
        raise HTTPException(404, "Área no encontrada")
    nombre = area.nombre
    db.execute(update(Evento).where(Evento.area_id == area_id).values(area_id=None))
    if actor is not None:
        registrar_actividad(db, actor, "area_eliminada", "area", str(area_id), titulo=nombre)
    db.delete(area)
    db.commit()
