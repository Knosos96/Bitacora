"""Rutas del tablero KPI."""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import usuario_actual
from app.models import Usuario
from app.schemas import CompromisoPendienteOut, KpiListaOut, TableroOut
from app.services.estados import es_gestor
from app.services.eventos import a_salida, compromiso_a_salida, hoy_en_zona
from app.services.kpi import NOMBRES, calcular, lista_de, semana_de

router = APIRouter(prefix="/kpi", tags=["kpi"])


def _solo_gestores(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    if not es_gestor(usuario.rol):
        raise HTTPException(403, "El tablero es para el encargado y el jefe")
    return usuario


def _rango(desde: date | None, hasta: date | None) -> tuple[date, date]:
    if desde is None and hasta is None:
        return semana_de(hoy_en_zona())
    desde = desde or hasta
    hasta = hasta or desde
    if desde > hasta:
        raise HTTPException(400, "'desde' no puede ser posterior a 'hasta'")
    if (hasta - desde).days > 366:
        raise HTTPException(400, "El rango máximo es de 366 días")
    return desde, hasta


@router.get("", response_model=TableroOut)
def tablero(desde: date | None = None, hasta: date | None = None, db: Session = Depends(get_db), _: Usuario = Depends(_solo_gestores)):
    d, h = _rango(desde, hasta)
    ahora = datetime.now(timezone.utc)
    return TableroOut(desde=d, hasta=h, generado_en=ahora, indicadores=calcular(db, d, h, hoy_en_zona(), ahora))


@router.get("/{kid}", response_model=KpiListaOut)
def lista_del_indicador(
    kid: str,
    desde: date | None = None,
    hasta: date | None = None,
    clave: str | None = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_gestores),
):
    kid = kid.upper()
    if kid not in NOMBRES:
        raise HTTPException(404, "Indicador desconocido")
    d, h = _rango(desde, hasta)
    try:
        eventos, comps, vacio = lista_de(db, kid, d, h, hoy_en_zona(), clave)
    except (ValueError, KeyError):
        raise HTTPException(400, "Subgrupo no válido para este indicador")
    return KpiListaOut(
        id=kid,
        nombre=NOMBRES[kid],
        texto_vacio=vacio,
        eventos=[a_salida(e) for e in eventos],
        compromisos=[
            CompromisoPendienteOut(
                **compromiso_a_salida(c, c.evento.folio).model_dump(),
                evento_titulo=c.evento.titulo,
                evento_tipo=c.evento.tipo,
            )
            for c in comps
        ],
    )
