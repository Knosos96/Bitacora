"""Funciones de pendientes."""
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import tiene_permiso
from app.core.enums import Estado, EstadoCompromiso, Permiso
from app.models import Compromiso, Evento, Usuario
from app.schemas import CompromisoPendienteOut, PendientesOut
from app.services.eventos import a_salida, compromiso_a_salida, con_relaciones, hoy_en_zona

NO_CERRADOS = (Estado.abierto, Estado.en_proceso, Estado.en_espera, Estado.resuelto)


def listar(db: Session, usuario: Usuario, solo_mios: bool = False, solo_vencidos: bool = False) -> PendientesOut:
    puede_ver_todos = tiene_permiso(usuario, Permiso.ver_kpi, Permiso.editar_cabecera)
    mios = solo_mios or not puede_ver_todos

    q_ev = con_relaciones().where(Evento.requiere_seguimiento, Evento.estado.in_(NO_CERRADOS))
    if mios:
        q_ev = q_ev.where(or_(Evento.responsable_id == usuario.id, Evento.autor_id == usuario.id))
    if solo_vencidos:
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
