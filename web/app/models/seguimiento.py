"""Modelo de notas de seguimiento (inmutables)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, Uuid, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.enums import Estado
from app.models.common import _ahora, _enum
from app.models.usuario import Usuario


class Seguimiento(Base):
    """Nota de seguimiento. Inmutable: no se edita ni se borra."""

    __tablename__ = "seguimiento"
    __table_args__ = (Index("ix_seguimiento_evento", "evento_id", "creado_en"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    evento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evento.id"))
    autor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"))
    nota: Mapped[str] = mapped_column(Text)
    estado_anterior: Mapped[Estado | None] = mapped_column(_enum(Estado, "estado_evento"))
    estado_nuevo: Mapped[Estado | None] = mapped_column(_enum(Estado, "estado_evento"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    autor: Mapped[Usuario] = relationship(foreign_keys=[autor_id])


@event.listens_for(Seguimiento, "before_update")
def _nota_inmutable_update(*_):
    raise ValueError("Las notas de seguimiento no se editan; agrega otra nota.")


@event.listens_for(Seguimiento, "before_delete")
def _nota_inmutable_delete(*_):
    raise ValueError("Las notas de seguimiento no se eliminan.")
