"""Esquemas de claves API."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ClaveApiIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)


class ClaveApiOut(BaseModel):
    id: uuid.UUID
    nombre: str
    prefijo: str
    creado_en: datetime
    revocada_en: datetime | None
    ultimo_uso: datetime | None
    usos: int


class ClaveApiCreada(ClaveApiOut):
    clave: str
