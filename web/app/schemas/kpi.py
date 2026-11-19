"""Esquemas del tablero KPI."""
from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.compromiso import CompromisoPendienteOut
from app.schemas.evento import EventoOut


class Indicador(BaseModel):
    id: str
    nombre: str
    valor: float | int | None
    unidad: str | None = None
    detalle: dict = {}


class TableroOut(BaseModel):
    desde: date
    hasta: date
    generado_en: datetime
    indicadores: list[Indicador]


class KpiListaOut(BaseModel):
    id: str
    nombre: str
    texto_vacio: str | None
    eventos: list[EventoOut]
    compromisos: list[CompromisoPendienteOut]
