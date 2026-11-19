"""Modelo de subtipo de evento."""
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.enums import Tipo
from app.models.common import _enum


class Subtipo(Base):
    """Ajustes al catálogo. Los de fábrica viven en enums.SUBTIPOS."""

    __tablename__ = "subtipo"

    tipo: Mapped[Tipo] = mapped_column(_enum(Tipo, "tipo_evento"), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), primary_key=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
