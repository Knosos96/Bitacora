"""Funciones de roles personalizados."""
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Permiso
from app.models import RolPersonalizado, Usuario
from app.schemas import RolPersonalizadoIn, RolPersonalizadoPatch
from app.services.historial import registrar_actividad, sincronizar_cuenta

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
    return [
        {"codigo": p.value, "descripcion": DESCRIPCIONES[p]}
        for p in Permiso
        if p != Permiso.ver_superadmin and p in DESCRIPCIONES
    ]


def _validar_permisos_custom(permisos: list[Permiso]) -> list[str]:
    if Permiso.ver_superadmin in permisos:
        raise HTTPException(409, {"codigo": "sin_permiso", "detalle": "El permiso de superusuario es exclusivo"})
    return [p.value for p in permisos]


def crear(db: Session, datos: RolPersonalizadoIn, jefe: Usuario) -> RolPersonalizado:
    nombre = datos.nombre.strip()
    if db.scalar(select(RolPersonalizado).where(RolPersonalizado.nombre == nombre)):
        raise HTTPException(400, "Ya existe un rol con ese nombre")
    rol = RolPersonalizado(
        nombre=nombre,
        descripcion=(datos.descripcion or "").strip(),
        permisos=_validar_permisos_custom(datos.permisos),
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
        nombre = datos.nombre.strip()
        existente = db.scalar(select(RolPersonalizado).where(
            RolPersonalizado.nombre == nombre, RolPersonalizado.id != rol_id))
        if existente:
            raise HTTPException(400, "Ya existe un rol con ese nombre")
        rol.nombre = nombre
    if datos.descripcion is not None:
        rol.descripcion = datos.descripcion.strip()
    if datos.permisos is not None:
        rol.permisos = _validar_permisos_custom(datos.permisos)
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
    db.flush()
    db.delete(rol)
    db.commit()


def asignar(db: Session, usuario_id: uuid.UUID, rol_id: uuid.UUID | None, actor: Usuario | None = None) -> dict:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None or usuario.eliminado_en is not None:
        raise HTTPException(404, "Usuario no encontrado")
    nombre_rol = None
    if rol_id is not None:
        rol = db.get(RolPersonalizado, rol_id)
        if rol is None or not rol.activo:
            raise HTTPException(404, "Rol no encontrado o inactivo")
        usuario.rol_custom_id = rol_id
        nombre_rol = rol.nombre
    else:
        usuario.rol_custom_id = None
    db.flush()
    sincronizar_cuenta(db, usuario)
    if actor is not None:
        registrar_actividad(
            db,
            actor,
            accion="rol_asignado",
            entidad="usuario",
            entidad_id=str(usuario.id),
            titulo=f"{usuario.nombre} ({usuario.correo})",
            detalle=f"Rol personalizado: {nombre_rol or 'ninguno (rol base)'}",
        )
    db.commit()
    return {"ok": True, "usuario_id": str(usuario_id), "rol_custom_id": str(rol_id) if rol_id else None}
