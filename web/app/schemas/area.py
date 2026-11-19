"""Esquemas de área."""
import uuid

from pydantic import BaseModel, ConfigDict, Field


class AreaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)


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
