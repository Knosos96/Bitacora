"""Rutas del tablero KPI."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import tiene_permiso, usuario_actual
from app.core.enums import Permiso
from app.models import Usuario
from app.schemas import KpiListaOut, TableroOut
from app.services import kpi as svc

router = APIRouter(prefix="/kpi", tags=["kpi"])


def _solo_gestores(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    if not tiene_permiso(usuario, Permiso.ver_kpi):
        raise HTTPException(403, "El tablero es para el encargado y el jefe")
    return usuario


@router.get("", response_model=TableroOut)
def tablero(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_gestores),
):
    return svc.obtener_tablero(db, desde, hasta)


@router.get("/{kid}", response_model=KpiListaOut)
def lista_del_indicador(
    kid: str,
    desde: date | None = None,
    hasta: date | None = None,
    clave: str | None = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_gestores),
):
    return svc.obtener_lista_indicador(db, kid, desde, hasta, clave)
