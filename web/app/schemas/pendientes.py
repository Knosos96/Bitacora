"""Esquemas de pendientes."""
from pydantic import BaseModel

from app.schemas.compromiso import CompromisoPendienteOut
from app.schemas.evento import EventoOut


class PendientesOut(BaseModel):
    eventos: list[EventoOut]
    compromisos: list[CompromisoPendienteOut]
