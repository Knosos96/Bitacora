from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import requiere_rol
from app.enums import Rol
from app.models import Usuario
from app.schemas import UsuarioIn, UsuarioOut
from app.security import hashear_clave

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.post("", response_model=UsuarioOut, status_code=201)
def crear_usuario(
    datos: UsuarioIn,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.jefe)),
):
    correo = datos.correo.lower()
    if db.scalar(select(Usuario).where(Usuario.correo == correo)):
        raise HTTPException(400, "Ya existe un usuario con ese correo")
    u = Usuario(nombre=datos.nombre, correo=correo, rol=datos.rol, clave_hash=hashear_clave(datos.clave))
    db.add(u)
    db.commit()
    return u


@router.get("", response_model=list[UsuarioOut])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.jefe, Rol.encargado)),
):
    return db.scalars(select(Usuario).order_by(Usuario.nombre)).all()
