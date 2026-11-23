"""Funciones de usuarios."""
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.deps import permisos_de
from app.core.enums import Rol
from app.core.security import hashear_clave
from app.models import (
    Auditoria,
    ClaveApi,
    Compromiso,
    Evento,
    RolPersonalizado,
    Seguimiento,
    Usuario,
)
from app.schemas import UsuarioIn, UsuarioOut, UsuarioPatch
from app.services.historial import (
    asegurar_respaldo_eventos_usuario,
    marcar_cuenta_eliminada,
    registrar_actividad,
    sincronizar_cuenta,
)


def a_salida(u: Usuario) -> UsuarioOut:
    return UsuarioOut(
        id=u.id,
        nombre=u.nombre,
        correo=u.correo,
        rol=u.rol,
        activo=u.activo,
        rol_custom_id=u.rol_custom_id,
        rol_custom_nombre=u.rol_custom.nombre if u.rol_custom else None,
        permisos=sorted(p.value for p in permisos_de(u)),
    )


def crear(db: Session, datos: UsuarioIn, actor: Usuario | None = None) -> UsuarioOut:
    if datos.rol == Rol.superusuario:
        raise HTTPException(409, {"codigo": "sin_permiso", "detalle": "No se pueden crear cuentas de superusuario aquí"})
    correo = datos.correo.lower()
    if db.scalar(select(Usuario).where(Usuario.correo == correo)):
        raise HTTPException(400, "Ya existe un usuario con ese correo")
    if datos.rol_custom_id is not None:
        rol_custom = db.get(RolPersonalizado, datos.rol_custom_id)
        if rol_custom is None or not rol_custom.activo:
            raise HTTPException(400, "El rol personalizado no existe o está inactivo")
    u = Usuario(
        nombre=datos.nombre.strip(),
        correo=correo,
        rol=datos.rol,
        rol_custom_id=datos.rol_custom_id,
        clave_hash=hashear_clave(datos.clave),
    )
    db.add(u)
    db.flush()
    u = db.scalar(
        select(Usuario).where(Usuario.id == u.id).options(joinedload(Usuario.rol_custom))
    )
    sincronizar_cuenta(db, u)
    registrar_actividad(
        db,
        actor or u,
        accion="usuario_creado",
        entidad="usuario",
        entidad_id=str(u.id),
        titulo=f"{u.nombre} ({u.correo})",
        detalle=f"Rol asignado: {u.rol_custom.nombre if u.rol_custom else u.rol.value}",
    )
    db.commit()
    return a_salida(u)


def listar(db: Session) -> list[UsuarioOut]:
    usuarios = db.scalars(
        select(Usuario)
        .options(joinedload(Usuario.rol_custom))
        .where(Usuario.rol != Rol.superusuario)
        .order_by(Usuario.nombre)
    ).all()
    return [a_salida(u) for u in usuarios]


def modificar(db: Session, usuario_id: uuid.UUID, datos: UsuarioPatch, jefe: Usuario) -> UsuarioOut:
    u = db.scalar(select(Usuario).where(Usuario.id == usuario_id).options(joinedload(Usuario.rol_custom)))
    if u is None:
        raise HTTPException(404, "Usuario no encontrado")
    if u.rol == Rol.superusuario and jefe.rol != Rol.superusuario:
        raise HTTPException(409, {"codigo": "sin_permiso", "detalle": "No puedes modificar una cuenta de superusuario"})
    if datos.rol == Rol.superusuario and jefe.rol != Rol.superusuario:
        raise HTTPException(409, {"codigo": "sin_permiso", "detalle": "No puedes asignar el rol superusuario"})

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

    cambios = []
    if datos.nombre is not None and datos.nombre.strip() != u.nombre:
        u.nombre = datos.nombre.strip()
        cambios.append("nombre")
    if datos.rol is not None and datos.rol != u.rol:
        u.rol = datos.rol
        cambios.append(f"rol={datos.rol.value}")
    if datos.activo is not None and datos.activo != u.activo:
        u.activo = datos.activo
        cambios.append("reactivado" if datos.activo else "desactivado")
    if datos.clave is not None:
        u.clave_hash = hashear_clave(datos.clave)
        cambios.append("clave_restablecida")

    sincronizar_cuenta(db, u)
    if cambios:
        accion = "usuario_desactivado" if datos.activo is False else ("usuario_reactivado" if datos.activo is True else "usuario_modificado")
        registrar_actividad(
            db,
            jefe,
            accion=accion,
            entidad="usuario",
            entidad_id=str(u.id),
            titulo=f"{u.nombre} ({u.correo})",
            detalle="Cambios: " + ", ".join(cambios),
        )
    db.commit()
    u = db.scalar(
        select(Usuario).where(Usuario.id == usuario_id).options(joinedload(Usuario.rol_custom))
    )
    return a_salida(u)


def eliminar(db: Session, usuario_id: uuid.UUID, jefe: Usuario) -> None:
    u = db.scalar(select(Usuario).where(Usuario.id == usuario_id).options(joinedload(Usuario.rol_custom)))
    if u is None:
        raise HTTPException(404, "Usuario no encontrado")
    if u.rol == Rol.superusuario:
        raise HTTPException(409, {"codigo": "sin_permiso", "detalle": "No puedes eliminar la cuenta de superusuario"})
    if u.id == jefe.id:
        raise HTTPException(409, {"codigo": "sin_permiso", "detalle": "No puedes eliminar tu propio usuario"})
    if u.rol == Rol.jefe and u.activo:
        otros = db.scalar(
            select(func.count()).select_from(Usuario).where(
                Usuario.rol == Rol.jefe, Usuario.activo, Usuario.id != u.id
            )
        )
        if not otros:
            raise HTTPException(409, {"codigo": "ultimo_jefe", "detalle": "Debe quedar al menos un jefe activo"})

    # Preserva el autor/responsable original en EventoOrigen y la cuenta en CuentaHistorica
    asegurar_respaldo_eventos_usuario(db, u)
    marcar_cuenta_eliminada(db, u, jefe)
    registrar_actividad(
        db,
        jefe,
        accion="usuario_eliminado",
        entidad="usuario",
        entidad_id=str(u.id),
        titulo=f"{u.nombre} ({u.correo})",
        detalle=f"Cuenta eliminada por {jefe.nombre} ({jefe.correo}); historial preservado.",
    )

    # Reasigna FKs en tablas operativas para mantener integridad referencial
    db.execute(update(Evento).where(Evento.responsable_id == usuario_id).values(responsable_id=None))
    db.execute(update(Evento).where(Evento.autor_id == usuario_id).values(autor_id=jefe.id))
    db.execute(update(Seguimiento).where(Seguimiento.autor_id == usuario_id).values(autor_id=jefe.id))
    db.execute(update(Compromiso).where(Compromiso.responsable_id == usuario_id).values(responsable_id=jefe.id))
    db.execute(update(Auditoria).where(Auditoria.usuario_id == usuario_id).values(usuario_id=jefe.id))
    db.execute(update(ClaveApi).where(ClaveApi.creada_por_id == usuario_id).values(creada_por_id=jefe.id))
    db.execute(update(RolPersonalizado).where(RolPersonalizado.creado_por_id == usuario_id).values(creado_por_id=jefe.id))

    db.delete(u)
    db.commit()
