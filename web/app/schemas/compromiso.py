"""Esquemas de compromiso."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.core.enums import EstadoCompromiso, Tipo
from app.schemas.common import validar_no_blanco
from app.schemas.usuario import UsuarioRef


class CompromisoIn(BaseModel):
    descripcion: str = Field(min_length=1, max_length=2000)
    fecha_limite: date
    responsable_id: uuid.UUID | None = None

    @field_validator("descripcion")
    @classmethod
    def _desc_valida(cls, v: str) -> str:
        return validar_no_blanco(v)


class CompromisoPatch(BaseModel):
    estado: EstadoCompromiso


class CompromisoOut(BaseModel):
    id: uuid.UUID
    evento_folio: str
    descripcion: str
    responsable: UsuarioRef
    fecha_limite: date
    estado: EstadoCompromiso
    vencido: bool
    cumplido_en: datetime | None
    creado_en: datetime


class CompromisoPendienteOut(CompromisoOut):
    evento_titulo: str
    evento_tipo: Tipo
