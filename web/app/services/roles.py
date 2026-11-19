"""Funciones de roles personalizados."""
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Permiso
from app.models import RolPersonalizado, Usuario
from app.schemas import RolPersonalizadoIn, RolPersonalizadoPatch

DESCRIPCIONES = {
    Permiso.ver_usuarios: "Ver la lista de usuarios",
    Permiso.crear_usuarios: "Crear nuevos usuarios",
    Permiso.editar_usuarios: "Cambiar nombre, rol, clave o estado de usuarios",
    Permiso.gestionar_roles: "Crear y editar roles personalizados",
    Permiso.ver_kpi: "Ver el tablero de indicadores KPI",
    Permiso.crear_eventos: "Registrar nuevos eventos",
    Permiso.editar_cabecera: "Corregir título, descripción y datos del evento",
    Permiso.cambiar_estado: "Avanzar el estado de un evento (hasta resuelto)",
    Permiso.cancelar_cerrar: "Cancelar o cerrar eventos",
    Permiso.reabrir_eventos: "Reabrir eventos cerrados o cancelados",
    Permiso.gestionar_compromisos: "Crear y resolver compromisos",
    Permiso.gestionar_areas: "Agregar y editar áreas",
    Permiso.gestionar_subtipos: "Agregar y editar subtipos de eventos",
    Permiso.gestionar_claves_api: "Emitir y revocar claves de API",
    Permiso.exportar_csv: "Exportar resultados a CSV",
}


def listar(db: Session, incluir_inactivos: bool = False):
    q = select(RolPersonalizado)
    if not incluir_inactivos:
        q = q.where(RolPersonalizado.activo.is_(True))
    return list(db.scalars(q.order_by(RolPersonalizado.nombre)).all())


def listar_permisos() -> list[dict]:
    return [{"codigo": p.value, "descripcion": DESCRIPCIONES[p]} for p in Permiso]


def crear(db: Session, datos: RolPersonalizadoIn, jefe: Usuario) -> RolPersonalizado:
    if db.scalar(select(RolPersonalizado).where(RolPersonalizado.nombre == datos.nombre)):
        raise HTTPException(400, "Ya existe un rol con ese nombre")
    rol = RolPersonalizado(
        nombre=datos.nombre,
        descripcion=datos.descripcion or "",
        permisos=[p.value for p in datos.permisos],
        creado_por_id=jefe.id,
    )
    db.add(rol)
    db.commit()
    return rol


def editar(db: Session, rol_id: uuid.UUID, datos: RolPersonalizadoPatch) -> RolPersonalizado:
    rol = db.get(RolPersonalizado, rol_id)
    if rol is None:
        raise HTTPException(404, "Rol no encontrado")
    if datos.nombre is not None:
        existente = db.scalar(select(RolPersonalizado).where(
            RolPersonalizado.nombre == datos.nombre, RolPersonalizado.id != rol_id))
        if existente:
            raise HTTPException(400, "Ya existe un rol con ese nombre")
        rol.nombre = datos.nombre
    if datos.descripcion is not None:
        rol.descripcion = datos.descripcion
    if datos.permisos is not None:
        rol.permisos = [p.value for p in datos.permisos]
    if datos.activo is not None:
        rol.activo = datos.activo
    db.commit()
    return rol


def eliminar(db: Session, rol_id: uuid.UUID) -> None:
    rol = db.get(RolPersonalizado, rol_id)
    if rol is None:
        raise HTTPException(404, "Rol no encontrado")
    for u in db.scalars(select(Usuario).where(Usuario.rol_custom_id == rol_id)).all():
        u.rol_custom_id = None
    rol.activo = False
    db.commit()


def asignar(db: Session, usuario_id: uuid.UUID, rol_id: uuid.UUID | None) -> dict:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(404, "Usuario no encontrado")
    if rol_id is not None:
        rol = db.get(RolPersonalizado, rol_id)
        if rol is None or not rol.activo:
            raise HTTPException(404, "Rol no encontrado o inactivo")
        usuario.rol_custom_id = rol_id
    else:
        usuario.rol_custom_id = None
    db.commit()
    return {"ok": True, "usuario_id": str(usuario_id), "rol_custom_id": str(rol_id) if rol_id else None}
