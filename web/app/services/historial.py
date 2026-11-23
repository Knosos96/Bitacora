"""Servicios de registro histórico inmutable de cuentas, eventos y actividad."""
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    ActividadBitacora,
    CuentaHistorica,
    Evento,
    EventoOrigen,
    Usuario,
    _ahora,
)


def sincronizar_cuenta(db: Session, u: Usuario, estado: str | None = None) -> CuentaHistorica:
    ahora = _ahora()
    est = estado or ("activa" if u.activo else "inactiva")
    rol_custom_nombre = u.rol_custom.nombre if getattr(u, "rol_custom", None) else None
    hist = db.get(CuentaHistorica, u.id)
    if hist is None:
        hist = CuentaHistorica(
            id=u.id,
            nombre=u.nombre,
            correo=u.correo,
            rol=u.rol.value if hasattr(u.rol, "value") else str(u.rol),
            rol_custom_nombre=rol_custom_nombre,
            estado=est,
            creado_en=u.creado_en or ahora,
            actualizado_en=ahora,
        )
        db.add(hist)
    else:
        hist.nombre = u.nombre
        hist.correo = u.correo
        hist.rol = u.rol.value if hasattr(u.rol, "value") else str(u.rol)
        hist.rol_custom_nombre = rol_custom_nombre
        hist.estado = est
        hist.actualizado_en = ahora
    return hist


def marcar_cuenta_eliminada(db: Session, u: Usuario, por: Usuario) -> None:
    hist = sincronizar_cuenta(db, u, estado="eliminada")
    ahora = _ahora()
    hist.eliminado_en = ahora
    hist.actualizado_en = ahora
    hist.eliminado_por_id = por.id
    hist.eliminado_por_nombre = por.nombre
    hist.eliminado_por_correo = por.correo


def registrar_evento_origen(
    db: Session,
    evento: Evento,
    autor: Usuario,
    responsable: Usuario | None = None,
) -> EventoOrigen:
    origen = db.get(EventoOrigen, evento.id)
    if origen is None:
        origen = EventoOrigen(
            evento_id=evento.id,
            autor_id=autor.id,
            autor_nombre=autor.nombre,
            autor_correo=autor.correo,
            responsable_id=responsable.id if responsable else None,
            responsable_nombre=responsable.nombre if responsable else None,
            responsable_correo=responsable.correo if responsable else None,
            creado_en=evento.creado_en or _ahora(),
        )
        db.add(origen)
    elif responsable is not None:
        origen.responsable_id = responsable.id
        origen.responsable_nombre = responsable.nombre
        origen.responsable_correo = responsable.correo
    elif evento.responsable_id is None:
        origen.responsable_id = None
        origen.responsable_nombre = None
        origen.responsable_correo = None
    return origen


def asegurar_respaldo_eventos_usuario(db: Session, u: Usuario) -> None:
    """Antes de borrar un Usuario, garantiza que todos sus eventos conserven su identidad original."""
    eventos = db.scalars(
        select(Evento)
        .options(joinedload(Evento.autor), joinedload(Evento.responsable))
        .where((Evento.autor_id == u.id) | (Evento.responsable_id == u.id))
    ).unique().all()
    for ev in eventos:
        origen = db.get(EventoOrigen, ev.id)
        if origen is None:
            registrar_evento_origen(db, ev, ev.autor, ev.responsable)


def registrar_actividad(
    db: Session,
    actor: Usuario | None,
    accion: str,
    entidad: str,
    entidad_id: str | None = None,
    folio: str | None = None,
    titulo: str | None = None,
    detalle: str = "",
) -> None:
    db.add(ActividadBitacora(
        actor_id=actor.id if actor else None,
        actor_nombre=actor.nombre if actor else "Sistema",
        actor_correo=actor.correo if actor else "sistema@local",
        actor_rol=(actor.rol.value if hasattr(actor.rol, "value") else str(actor.rol)) if actor else "sistema",
        accion=accion,
        entidad=entidad,
        entidad_id=str(entidad_id) if entidad_id else None,
        folio=folio,
        titulo=titulo[:250] if titulo else None,
        detalle=detalle,
        creado_en=_ahora(),
    ))


def sincronizar_existentes(db: Session) -> None:
    """Rellena CuentaHistorica y EventoOrigen para registros creados antes del módulo de historial."""
    usuarios = db.scalars(select(Usuario).options(joinedload(Usuario.rol_custom))).all()
    existentes_cuentas = set(db.scalars(select(CuentaHistorica.id)).all())
    hubo = False
    for u in usuarios:
        if u.id not in existentes_cuentas:
            sincronizar_cuenta(db, u)
            hubo = True

    existentes_origen = set(db.scalars(select(EventoOrigen.evento_id)).all())
    eventos = db.scalars(
        select(Evento).options(joinedload(Evento.autor), joinedload(Evento.responsable))
    ).unique().all()
    for ev in eventos:
        if ev.id not in existentes_origen:
            registrar_evento_origen(db, ev, ev.autor, ev.responsable)
            hubo = True
    if hubo:
        db.commit()
