"""Rutas exclusivas del portal documental de Superusuario."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import requiere_rol
from app.core.enums import Estado, Rol, Tipo
from app.models import Usuario
from app.schemas.superadmin import (
    ActividadOut,
    CuentaHistoricaOut,
    ExpedienteCuentaOut,
    RegistroHistoricoOut,
    SuperArchivosOut,
    SuperPendientesOut,
    SuperResumenOut,
)
from app.services import superadmin as svc

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


@router.get("/resumen", response_model=SuperResumenOut)
def resumen(
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.superusuario)),
):
    return svc.resumen(db)


@router.get("/cuentas", response_model=list[CuentaHistoricaOut])
def cuentas(
    estado: str | None = Query(None, pattern="^(activa|inactiva|eliminada)$"),
    q: str | None = Query(None, max_length=120),
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.superusuario)),
):
    return svc.listar_cuentas(db, estado=estado, q=q)


@router.get("/cuentas/{cuenta_id}", response_model=ExpedienteCuentaOut)
def expediente_cuenta(
    cuenta_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.superusuario)),
):
    return svc.expediente_cuenta(db, cuenta_id)


@router.get("/registros", response_model=list[RegistroHistoricoOut])
def registros(
    cuenta_id: uuid.UUID | None = None,
    tipo: Tipo | None = None,
    estado: Estado | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = Query(None, max_length=200),
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.superusuario)),
):
    return svc.listar_registros(db, cuenta_id=cuenta_id, tipo=tipo, estado=estado, desde=desde, hasta=hasta, q=q)


@router.get("/pendientes", response_model=SuperPendientesOut)
def pendientes(
    cuenta_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.superusuario)),
):
    return svc.listar_pendientes(db, cuenta_id=cuenta_id)


@router.get("/archivos", response_model=SuperArchivosOut)
def archivos(
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.superusuario)),
):
    return svc.listar_archivos(db)


@router.get("/actividad", response_model=list[ActividadOut])
def actividad(
    cuenta_id: uuid.UUID | None = None,
    accion: str | None = Query(None, max_length=60),
    entidad: str | None = Query(None, max_length=40),
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = Query(None, max_length=200),
    limit: int = Query(250, ge=1, le=2000),
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.superusuario)),
):
    return svc.listar_actividad(
        db, cuenta_id=cuenta_id, accion=accion, entidad=entidad,
        desde=desde, hasta=hasta, q=q, limit=limit,
    )


@router.get("/exportar")
def exportar_dossier(
    seccion: str = Query("actividad", pattern="^(actividad|cuentas|registros)$"),
    cuenta_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.superusuario)),
):
    cuerpo, nombre = svc.exportar_dossier_csv(db, seccion=seccion, cuenta_id=cuenta_id)
    return Response(
        cuerpo,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
