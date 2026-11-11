from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.deps import usuario_actual
from app.enums import Estado, EstadoCompromiso, Rol
from app.models import Compromiso, Evento, Usuario
from app.routers.eventos import _con_relaciones, a_salida, compromiso_a_salida, hoy_en_zona
from app.schemas import CompromisoPendienteOut, PendientesOut

router = APIRouter(prefix="/pendientes", tags=["pendientes"])

NO_CERRADOS = (Estado.abierto, Estado.en_proceso, Estado.en_espera, Estado.resuelto)


@router.get("", response_model=PendientesOut)
def pendientes(
    solo_mios: bool = False,
    solo_vencidos: bool = Query(False, description="Solo compromisos pendientes con fecha límite anterior a hoy"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    """CU-15. Eventos con seguimiento no cerrados y compromisos pendientes.

    El asistente ve solo los suyos; encargado y jefe ven todos (o los suyos con solo_mios).
    """
    mios = solo_mios or usuario.rol == Rol.asistente

    q_ev = _con_relaciones().where(Evento.requiere_seguimiento, Evento.estado.in_(NO_CERRADOS))
    if mios:
        q_ev = q_ev.where(or_(Evento.responsable_id == usuario.id, Evento.autor_id == usuario.id))
    if solo_vencidos:
        # Solo los eventos que tienen al menos un compromiso vencido.
        vencidos_ev = select(Compromiso.evento_id).where(
            Compromiso.estado == EstadoCompromiso.pendiente, Compromiso.fecha_limite < hoy_en_zona()
        )
        q_ev = q_ev.where(Evento.id.in_(vencidos_ev))
    eventos = db.scalars(q_ev.order_by(Evento.fecha_hecho, Evento.creado_en)).unique().all()

    q_c = (
        select(Compromiso)
        .options(joinedload(Compromiso.responsable), joinedload(Compromiso.evento))
        .where(Compromiso.estado == EstadoCompromiso.pendiente)
    )
    if mios:
        q_c = q_c.where(Compromiso.responsable_id == usuario.id)
    if solo_vencidos:
        q_c = q_c.where(Compromiso.fecha_limite < hoy_en_zona())
    compromisos = db.scalars(q_c.order_by(Compromiso.fecha_limite, Compromiso.creado_en)).unique().all()

    return PendientesOut(
        eventos=[a_salida(e) for e in eventos],
        compromisos=[
            CompromisoPendienteOut(
                **compromiso_a_salida(c, c.evento.folio).model_dump(),
                evento_titulo=c.evento.titulo,
                evento_tipo=c.evento.tipo,
            )
            for c in compromisos
        ],
    )
