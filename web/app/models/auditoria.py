"""Modelo de auditoría de cabecera de evento."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.common import _ahora
from app.models.usuario import Usuario


class Auditoria(Base):
    """Correcciones de la cabecera del evento."""

    __tablename__ = "auditoria"
    __table_args__ = (Index("ix_auditoria_evento", "evento_id", "creado_en"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    evento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evento.id"))
    campo: Mapped[str] = mapped_column(String(40))
    valor_anterior: Mapped[str | None] = mapped_column(Text)
    valor_nuevo: Mapped[str | None] = mapped_column(Text)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id])
