"""Funciones de compromisos."""
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.deps import tiene_permiso
from app.core.enums import Estado, EstadoCompromiso, Permiso
from app.models import Compromiso, Evento, Seguimiento, Usuario, _ahora
from app.schemas import CompromisoOut, CompromisoPatch
from app.services.eventos import compromiso_a_salida, conflicto
from app.services.historial import registrar_actividad


def resolver(db: Session, compromiso_id: uuid.UUID, datos: CompromisoPatch, usuario: Usuario) -> CompromisoOut:
    c = db.get(Compromiso, compromiso_id, options=[joinedload(Compromiso.responsable), joinedload(Compromiso.evento)])
    if c is None:
        raise HTTPException(404, "Compromiso no encontrado")
    if datos.estado == EstadoCompromiso.pendiente:
        raise HTTPException(400, "Solo se puede marcar como cumplido o cancelado")
    if c.estado != EstadoCompromiso.pendiente:
        raise conflicto("transicion_invalida", f"El compromiso ya está {c.estado.value}")
    es_gestor_comp = tiene_permiso(usuario, Permiso.cancelar_cerrar, Permiso.editar_cabecera)
    puede_propio = tiene_permiso(usuario, Permiso.gestionar_compromisos) and usuario.id == c.responsable_id
    if not (es_gestor_comp or puede_propio):
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
    registrar_actividad(
        db,
        usuario,
        accion=f"compromiso_{datos.estado.value}",
        entidad="compromiso",
        entidad_id=str(c.id),
        folio=ev.folio,
        titulo=c.descripcion,
        detalle=f"Estado actualizado a {datos.estado.value}",
    )
    db.commit()
    return compromiso_a_salida(c, ev.folio)
