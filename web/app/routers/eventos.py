"""Rutas de eventos, seguimientos, compromisos y exportación CSV."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Acceso, acceso_lectura, requiere_permiso, usuario_actual
from app.core.enums import Estado, Permiso, Tipo
from app.models import Usuario
from app.schemas import (
    CambioEstadoIn,
    CompromisoIn,
    CompromisoOut,
    EventoDetalleOut,
    EventoIn,
    EventoOut,
    EventoPatch,
    EventosPagina,
    SeguimientoIn,
    SeguimientoOut,
)
from app.services import eventos as svc

router = APIRouter(prefix="/eventos", tags=["eventos"])


@router.post("", response_model=EventoOut, status_code=201)
def crear_evento(
    datos: EventoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_permiso(Permiso.crear_eventos)),
):
    return svc.crear(db, datos, usuario)


@router.get("", response_model=EventosPagina)
def listar_eventos(
    desde: date | None = None,
    hasta: date | None = None,
    tipo: list[Tipo] = Query(default=[]),
    estado: list[Estado] = Query(default=[]),
    q: str | None = Query(None, max_length=200, description="Texto a buscar (CU-11) o un folio"),
    area_id: uuid.UUID | None = None,
    responsable_id: uuid.UUID | None = None,
    seguimiento: str | None = Query(None, pattern="^(con|sin)$"),
    vencidos: bool = Query(False, description="Solo eventos con compromisos pendientes vencidos"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    acceso: Acceso = Depends(acceso_lectura),
):
    """CU-11, CU-12, CU-19 y CU-20. Sin filtros ni fechas es la pantalla Hoy."""
    return svc.listar(
        db=db,
        acceso=acceso,
        desde=desde,
        hasta=hasta,
        tipo=tipo,
        estado=estado,
        q=q,
        area_id=area_id,
        responsable_id=responsable_id,
        seguimiento=seguimiento,
        vencidos=vencidos,
        page=page,
        page_size=page_size,
    )


@router.get("/resumen")
def resumen(
    desde: date,
    hasta: date,
    tipo: list[Tipo] = Query(default=[]),
    db: Session = Depends(get_db),
    _: Acceso = Depends(acceso_lectura),
):
    """CU-21 / sección 10.3: conteos por tipo sin traer el detalle."""
    return svc.resumen(db, desde, hasta, tipo)


@router.get("/exportar")
def exportar_csv(
    desde: date | None = None,
    hasta: date | None = None,
    tipo: list[Tipo] = Query(default=[]),
    estado: list[Estado] = Query(default=[]),
    q: str | None = Query(None, max_length=200),
    area_id: uuid.UUID | None = None,
    responsable_id: uuid.UUID | None = None,
    seguimiento: str | None = Query(None, pattern="^(con|sin)$"),
    vencidos: bool = False,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_permiso(Permiso.exportar_csv)),
):
    """CU-22. Mismo filtro que la lista, sin paginar."""
    cuerpo, nombre = svc.exportar_csv(
        db=db,
        desde=desde,
        hasta=hasta,
        tipo=tipo,
        estado=estado,
        q=q,
        area_id=area_id,
        responsable_id=responsable_id,
        seguimiento=seguimiento,
        vencidos=vencidos,
        actor=usuario,
    )
    return Response(
        cuerpo,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/{folio}", response_model=EventoDetalleOut)
def obtener_evento(
    folio: str,
    incluir: list[str] = Query(default=[], description="seguimientos, compromisos, auditoria (separados por coma o repetidos)"),
    db: Session = Depends(get_db),
    acceso: Acceso = Depends(acceso_lectura),
):
    return svc.obtener(db, folio, incluir, acceso)


@router.patch("/{folio}", response_model=EventoOut)
def modificar_evento(
    folio: str,
    datos: EventoPatch,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    """CU-04 (seguimiento), CU-05 (responsable y prioridad) y CU-23 (corregir cabecera)."""
    return svc.modificar(db, folio, datos, usuario)


@router.post("/{folio}/estado", response_model=EventoOut)
def cambiar_estado(
    folio: str,
    datos: CambioEstadoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    """CU-08 y CU-09. Cada cambio escribe una nota automática además de la nota de la persona."""
    return svc.cambiar_estado(db, folio, datos, usuario)


@router.get("/{folio}/seguimientos", response_model=list[SeguimientoOut])
def listar_seguimientos(folio: str, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return svc.obtener_seguimientos(db, folio)


@router.post("/{folio}/seguimientos", response_model=SeguimientoOut, status_code=201)
def agregar_nota(
    folio: str,
    datos: SeguimientoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    """CU-07. La nota no se edita. En un evento cerrado solo encargado/jefe, y no lo reabre."""
    return svc.agregar_nota(db, folio, datos, usuario)


@router.get("/{folio}/compromisos", response_model=list[CompromisoOut])
def listar_compromisos(folio: str, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return svc.obtener_compromisos(db, folio)


@router.post("/{folio}/compromisos", response_model=CompromisoOut, status_code=201)
def crear_compromiso(
    folio: str,
    datos: CompromisoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_permiso(Permiso.gestionar_compromisos)),
):
    """CU-06. Requiere seguimiento y que el evento no esté cerrado ni cancelado."""
    return svc.crear_compromiso(db, folio, datos, usuario)
