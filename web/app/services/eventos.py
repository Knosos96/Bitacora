"""Funciones de dominio de eventos (sin capa HTTP)."""
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.enums import Estado, EstadoCompromiso, Prioridad
from app.models import Area, Auditoria, Compromiso, Evento, Seguimiento, Usuario, _ahora
from app.schemas import (
    AreaRef, AuditoriaOut, CompromisoOut, EventoOut, SeguimientoOut, UsuarioRef,
)
from app.services.busqueda import reindexar
from app.services.estados import es_gestor
from app.services.subtipos import vigentes


def hoy_en_zona() -> date:
    return datetime.now(ZoneInfo(settings.zona_horaria)).date()


def a_salida(e: Evento) -> EventoOut:
    return EventoOut(
        id=e.id,
        folio=e.folio,
        tipo=e.tipo,
        subtipo=e.subtipo,
        titulo=e.titulo,
        descripcion=e.descripcion,
        referencia=e.referencia,
        fecha_hecho=e.fecha_hecho,
        estado=e.estado,
        requiere_seguimiento=e.requiere_seguimiento,
        prioridad=e.prioridad,
        area_origen=AreaRef.model_validate(e.area) if e.area else None,
        solicitante=e.solicitante_nombre,
        autor=UsuarioRef.model_validate(e.autor),
        responsable=UsuarioRef.model_validate(e.responsable) if e.responsable else None,
        creado_en=e.creado_en,
        cerrado_en=e.cerrado_en,
    )


def con_relaciones():
    return select(Evento).options(
        joinedload(Evento.area), joinedload(Evento.autor), joinedload(Evento.responsable)
    )


# alias usado por kpi/pendientes
_con_relaciones = con_relaciones


def conflicto(codigo: str, detalle: str) -> HTTPException:
    return HTTPException(409, {"codigo": codigo, "detalle": detalle})


def buscar_evento(db: Session, folio: str) -> Evento:
    try:
        condicion = Evento.id == uuid.UUID(folio)
    except ValueError:
        condicion = Evento.folio == folio.upper()
    e = db.scalars(
        con_relaciones().where(condicion).execution_options(populate_existing=True)
    ).unique().one_or_none()
    if e is None:
        raise HTTPException(404, "Evento no encontrado")
    return e


def compromiso_a_salida(c: Compromiso, folio: str) -> CompromisoOut:
    return CompromisoOut(
        id=c.id,
        evento_folio=folio,
        descripcion=c.descripcion,
        responsable=UsuarioRef.model_validate(c.responsable),
        fecha_limite=c.fecha_limite,
        estado=c.estado,
        vencido=c.estado == EstadoCompromiso.pendiente and c.fecha_limite < hoy_en_zona(),
        cumplido_en=c.cumplido_en,
        creado_en=c.creado_en,
    )


def usuario_activo(db: Session, usuario_id: uuid.UUID) -> bool:
    u = db.get(Usuario, usuario_id)
    return bool(u and u.activo)


def nota(db: Session, e: Evento, autor: Usuario, texto: str, anterior=None, nuevo=None) -> Seguimiento:
    n = Seguimiento(
        evento_id=e.id, autor_id=autor.id, nota=texto, estado_anterior=anterior, estado_nuevo=nuevo,
        creado_en=_ahora(),
    )
    db.add(n)
    return n


def pendientes_del_evento(db: Session, e: Evento) -> list[Compromiso]:
    return list(
        db.scalars(
            select(Compromiso).where(
                Compromiso.evento_id == e.id, Compromiso.estado == EstadoCompromiso.pendiente
            )
        ).all()
    )


def lista_seguimientos(db: Session, e: Evento) -> list[SeguimientoOut]:
    filas = db.scalars(
        select(Seguimiento)
        .options(joinedload(Seguimiento.autor))
        .where(Seguimiento.evento_id == e.id)
        .order_by(Seguimiento.creado_en, Seguimiento.id)
    ).all()
    return [SeguimientoOut.model_validate(n) for n in filas]


def lista_compromisos(db: Session, e: Evento) -> list[CompromisoOut]:
    filas = db.scalars(
        select(Compromiso)
        .options(joinedload(Compromiso.responsable))
        .where(Compromiso.evento_id == e.id)
        .order_by(Compromiso.fecha_limite, Compromiso.creado_en)
    ).all()
    return [compromiso_a_salida(c, e.folio) for c in filas]
