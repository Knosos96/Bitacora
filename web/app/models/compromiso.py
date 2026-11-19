"""Modelo de compromiso."""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.enums import EstadoCompromiso
from app.models.common import _ahora, _enum
from app.models.evento import Evento
from app.models.usuario import Usuario


class Compromiso(Base):
    __tablename__ = "compromiso"
    __table_args__ = (
        Index("ix_compromiso_evento", "evento_id"),
        Index("ix_compromiso_estado_fecha", "estado", "fecha_limite"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    evento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evento.id"))
    descripcion: Mapped[str] = mapped_column(Text)
    responsable_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"))
    fecha_limite: Mapped[date] = mapped_column(Date)
    estado: Mapped[EstadoCompromiso] = mapped_column(
        _enum(EstadoCompromiso, "estado_compromiso"), default=EstadoCompromiso.pendiente
    )
    cumplido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    evento: Mapped[Evento] = relationship(foreign_keys=[evento_id])
    responsable: Mapped[Usuario] = relationship(foreign_keys=[responsable_id])
