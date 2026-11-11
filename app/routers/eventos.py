import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.db import get_db
from app.deps import usuario_actual
from app.enums import Estado, Prioridad, Tipo
from app.folio import siguiente_folio
from app.models import Area, Evento, Usuario
from app.schemas import AreaRef, EventoIn, EventoOut, EventosPagina, Meta, UsuarioRef

router = APIRouter(prefix="/eventos", tags=["eventos"])


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


def _con_relaciones():
    return select(Evento).options(
        joinedload(Evento.area), joinedload(Evento.autor), joinedload(Evento.responsable)
    )


@router.post("", response_model=EventoOut, status_code=201)
def crear_evento(
    datos: EventoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    if datos.area_id and not db.get(Area, datos.area_id):
        raise HTTPException(400, "El área no existe")

    fecha = datos.fecha_hecho or hoy_en_zona()
    if fecha > hoy_en_zona():
        raise HTTPException(400, "La fecha del hecho no puede estar en el futuro")

    responsable_id = None
    prioridad = None
    estado = Estado.informativo
    if datos.requiere_seguimiento:
        estado = Estado.abierto
        responsable_id = datos.responsable_id or usuario.id  # por defecto, el autor
        prioridad = datos.prioridad or Prioridad.media
        if not db.get(Usuario, responsable_id):
            raise HTTPException(400, "El responsable no existe")

    evento = Evento(
        folio=siguiente_folio(db, fecha.year),
        tipo=datos.tipo,
        subtipo=datos.subtipo,
        titulo=datos.titulo.strip(),
        descripcion=datos.descripcion.strip(),
        referencia=datos.referencia,
        fecha_hecho=fecha,
        area_id=datos.area_id,
        solicitante_nombre=datos.solicitante_nombre,
        requiere_seguimiento=datos.requiere_seguimiento,
        estado=estado,
        prioridad=prioridad,
        autor_id=usuario.id,
        responsable_id=responsable_id,
    )
    db.add(evento)
    db.commit()
    evento = db.scalars(_con_relaciones().where(Evento.id == evento.id)).unique().one()
    return a_salida(evento)


@router.get("", response_model=EventosPagina)
def listar_eventos(
    desde: date | None = None,
    hasta: date | None = None,
    tipo: list[Tipo] = Query(default=[]),
    estado: list[Estado] = Query(default=[]),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    # Sin fechas, la pantalla Hoy: el día operativo del área.
    if desde is None and hasta is None:
        desde = hasta = hoy_en_zona()
    desde = desde or hasta
    hasta = hasta or desde
    if desde > hasta:
        raise HTTPException(400, "'desde' no puede ser posterior a 'hasta'")
    if (hasta - desde).days > 366:
        raise HTTPException(400, "El rango máximo es de 366 días")

    filtros = [Evento.fecha_hecho >= desde, Evento.fecha_hecho <= hasta]
    if tipo:
        filtros.append(Evento.tipo.in_(tipo))
    if estado:
        filtros.append(Evento.estado.in_(estado))

    total = db.scalar(select(func.count()).select_from(Evento).where(*filtros))
    filas = (
        db.scalars(
            _con_relaciones()
            .where(*filtros)
            .order_by(Evento.fecha_hecho.desc(), Evento.creado_en.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .all()
    )
    return EventosPagina(
        data=[a_salida(e) for e in filas],
        meta=Meta(page=page, page_size=page_size, total=total),
    )


@router.get("/{folio}", response_model=EventoOut)
def obtener_evento(folio: str, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    """Acepta el folio (BIT-2026-00041) o el uuid."""
    try:
        condicion = Evento.id == uuid.UUID(folio)
    except ValueError:
        condicion = Evento.folio == folio.upper()
    e = db.scalars(_con_relaciones().where(condicion)).unique().one_or_none()
    if e is None:
        raise HTTPException(404, "Evento no encontrado")
    return a_salida(e)
