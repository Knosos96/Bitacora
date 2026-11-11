from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import requiere_rol, usuario_actual
from app.enums import Rol
from app.models import Area, Usuario
from app.schemas import AreaIn, AreaOut

router = APIRouter(prefix="/areas", tags=["areas"])


@router.get("", response_model=list[AreaOut])
def listar_areas(db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return db.scalars(select(Area).where(Area.activa).order_by(Area.nombre)).all()


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
