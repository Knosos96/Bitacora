"""Esquemas de evento, seguimiento y auditoría."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import Estado, Prioridad, Tipo
from app.schemas.area import AreaRef
from app.schemas.common import validar_no_blanco
from app.schemas.compromiso import CompromisoOut
from app.schemas.usuario import UsuarioRef


class EventoIn(BaseModel):
    tipo: Tipo
    subtipo: str | None = None
    titulo: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(min_length=1, max_length=20000)
    referencia: str | None = Field(default=None, max_length=500)
    fecha_hecho: date | None = None
    area_id: uuid.UUID | None = None
    solicitante_nombre: str | None = Field(default=None, max_length=120)
    requiere_seguimiento: bool = False
    prioridad: Prioridad | None = None
    responsable_id: uuid.UUID | None = None

    @field_validator("titulo", "descripcion")
    @classmethod
    def _no_blanco(cls, v: str) -> str:
        return validar_no_blanco(v)


class EventoOut(BaseModel):
    """Contrato de la sección 10.1. No renombrar campos."""

    id: uuid.UUID
    folio: str
    tipo: Tipo
    subtipo: str | None
    titulo: str
    descripcion: str
    referencia: str | None
    fecha_hecho: date
    estado: Estado
    requiere_seguimiento: bool
    prioridad: Prioridad | None
    area_origen: AreaRef | None
    solicitante: str | None
    autor: UsuarioRef
    responsable: UsuarioRef | None
    creado_en: datetime
    cerrado_en: datetime | None


class Meta(BaseModel):
    page: int
    page_size: int
    total: int


class EventoBusquedaOut(EventoOut):
    fragmento: str | None = None


class EventosPagina(BaseModel):
    data: list[EventoBusquedaOut]
    meta: Meta


class EventoPatch(BaseModel):
    requiere_seguimiento: bool | None = None
    responsable_id: uuid.UUID | None = None
    prioridad: Prioridad | None = None
    nota: str | None = Field(default=None, max_length=5000)
    tipo: Tipo | None = None
    subtipo: str | None = None
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, min_length=1, max_length=20000)
    referencia: str | None = Field(default=None, max_length=500)
    fecha_hecho: date | None = None
    area_id: uuid.UUID | None = None
    solicitante_nombre: str | None = Field(default=None, max_length=120)

    @field_validator("titulo", "descripcion")
    @classmethod
    def _no_blanco(cls, v: str | None) -> str | None:
        return validar_no_blanco(v)


class CambioEstadoIn(BaseModel):
    estado: Estado
    nota: str | None = Field(default=None, max_length=5000)
    resolver_compromisos: str | None = Field(default=None, pattern="^(cumplir|cancelar)$")


class SeguimientoIn(BaseModel):
    nota: str = Field(min_length=1, max_length=5000)

    @field_validator("nota")
    @classmethod
    def _no_blanco(cls, v: str) -> str:
        return validar_no_blanco(v)


class SeguimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    autor: UsuarioRef
    nota: str
    estado_anterior: Estado | None
    estado_nuevo: Estado | None
    creado_en: datetime


class AuditoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    campo: str
    valor_anterior: str | None
    valor_nuevo: str | None
    usuario: UsuarioRef
    creado_en: datetime


class EventoDetalleOut(EventoOut):
    seguimientos: list[SeguimientoOut] | None = None
    compromisos: list[CompromisoOut] | None = None
    auditoria: list[AuditoriaOut] | None = None
