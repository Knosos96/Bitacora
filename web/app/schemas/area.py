"""Esquemas de área."""
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import validar_no_blanco


class AreaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)

    @field_validator("nombre")
    @classmethod
    def _nombre_valido(cls, v: str) -> str:
        return validar_no_blanco(v)


class AreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    activa: bool


class AreaRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str


class AreaPatch(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    activa: bool | None = None

    @field_validator("nombre")
    @classmethod
    def _nombre_valido(cls, v: str | None) -> str | None:
        return validar_no_blanco(v)
