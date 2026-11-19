"""Funciones de compromisos."""
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.enums import Estado, EstadoCompromiso
from app.models import Compromiso, Evento, Seguimiento, Usuario, _ahora
from app.schemas import CompromisoOut, CompromisoPatch
from app.services.estados import es_gestor
from app.services.eventos import compromiso_a_salida, conflicto


def resolver(db: Session, compromiso_id: uuid.UUID, datos: CompromisoPatch, usuario: Usuario) -> CompromisoOut:
    c = db.get(Compromiso, compromiso_id, options=[joinedload(Compromiso.responsable), joinedload(Compromiso.evento)])
    if c is None:
        raise HTTPException(404, "Compromiso no encontrado")
    if datos.estado == EstadoCompromiso.pendiente:
        raise HTTPException(400, "Solo se puede marcar como cumplido o cancelado")
    if c.estado != EstadoCompromiso.pendiente:
        raise conflicto("transicion_invalida", f"El compromiso ya está {c.estado.value}")
    if not (es_gestor(usuario.rol) or usuario.id == c.responsable_id):
        raise conflicto("sin_permiso", "Solo el responsable, el encargado o el jefe lo resuelven")
    ev: Evento = c.evento
    if ev.estado in (Estado.cerrado, Estado.cancelado):
        raise conflicto("evento_cerrado", "El evento está cerrado o cancelado")

    c.estado = datos.estado
    if datos.estado == EstadoCompromiso.cumplido:
        c.cumplido_en = _ahora()
    db.add(Seguimiento(
        evento_id=ev.id, autor_id=usuario.id,
        nota=f"Compromiso {datos.estado.value}: {c.descripcion}",
    ))
    db.commit()
    return compromiso_a_salida(c, ev.folio)
