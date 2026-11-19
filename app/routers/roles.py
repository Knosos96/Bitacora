"""Sprint 7: Roles personalizados. Solo el jefe puede gestionarlos."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import requiere_rol
from app.enums import Permiso, Rol
from app.models import RolPersonalizado, Usuario
from app.schemas import RolPersonalizadoIn, RolPersonalizadoOut, RolPersonalizadoPatch

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RolPersonalizadoOut])
def listar_roles(
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.jefe, Rol.encargado)),
):
    """Lista todos los roles personalizados. El encargado puede ver pero no modificar."""
    q = select(RolPersonalizado)
    if not incluir_inactivos:
        q = q.where(RolPersonalizado.activo.is_(True))
    return db.scalars(q.order_by(RolPersonalizado.nombre)).all()


@router.get("/permisos", response_model=list[dict])
def listar_permisos(_: Usuario = Depends(requiere_rol(Rol.jefe))):
    """Devuelve todos los permisos disponibles con su descripción."""
    descripciones = {
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
    return [{"codigo": p.value, "descripcion": descripciones[p]} for p in Permiso]


@router.post("", response_model=RolPersonalizadoOut, status_code=201)
def crear_rol(
    datos: RolPersonalizadoIn,
    db: Session = Depends(get_db),
    jefe: Usuario = Depends(requiere_rol(Rol.jefe)),
):
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


@router.patch("/{rol_id}", response_model=RolPersonalizadoOut)
def editar_rol(
    rol_id: uuid.UUID,
    datos: RolPersonalizadoPatch,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.jefe)),
):
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


@router.delete("/{rol_id}", status_code=204)
def eliminar_rol(
    rol_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.jefe)),
):
    """Desactiva el rol (no lo borra) y quita la asignación de los usuarios que lo tenían."""
    rol = db.get(RolPersonalizado, rol_id)
    if rol is None:
        raise HTTPException(404, "Rol no encontrado")
    # Quitar el rol a todos los usuarios que lo tenían
    usuarios = db.scalars(select(Usuario).where(Usuario.rol_custom_id == rol_id)).all()
    for u in usuarios:
        u.rol_custom_id = None
    rol.activo = False
    db.commit()


@router.post("/asignar", response_model=dict)
def asignar_rol(
    usuario_id: uuid.UUID,
    rol_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.jefe)),
):
    """Asigna o quita un rol personalizado a un usuario. rol_id=null quita el rol personalizado."""
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

