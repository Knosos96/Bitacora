import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import requiere_rol
from app.enums import Rol
from app.models import Usuario
from app.schemas import UsuarioIn, UsuarioOut, UsuarioPatch
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


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def modificar_usuario(
    usuario_id: uuid.UUID,
    datos: UsuarioPatch,
    db: Session = Depends(get_db),
    jefe: Usuario = Depends(requiere_rol(Rol.jefe)),
):
    """CU-16. Cambiar nombre o rol, desactivar o reactivar, restablecer la clave. No se borra a nadie."""
    u = db.get(Usuario, usuario_id)
    if u is None:
        raise HTTPException(404, "Usuario no encontrado")

    deja_de_ser_jefe_activo = u.rol == Rol.jefe and u.activo and (
        datos.activo is False or (datos.rol is not None and datos.rol != Rol.jefe)
    )
    if deja_de_ser_jefe_activo:
        otros = db.scalar(
            select(func.count()).select_from(Usuario).where(
                Usuario.rol == Rol.jefe, Usuario.activo, Usuario.id != u.id)
        )
        if u.id == jefe.id and datos.activo is False:
            raise HTTPException(409, {"codigo": "sin_permiso", "detalle": "No puedes desactivarte a ti mismo"})
        if not otros:
            raise HTTPException(409, {"codigo": "ultimo_jefe", "detalle": "Debe quedar al menos un jefe activo"})

    if datos.nombre is not None:
        u.nombre = datos.nombre.strip()
    if datos.rol is not None:
        u.rol = datos.rol
    if datos.activo is not None:
        u.activo = datos.activo
    if datos.clave is not None:
        u.clave_hash = hashear_clave(datos.clave)
    db.commit()
    return u
