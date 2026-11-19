"""Modelo de evento."""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.enums import Estado, Prioridad, Tipo
from app.models.area import Area
from app.models.common import _ahora, _enum
from app.models.usuario import Usuario


class Evento(Base):
    __tablename__ = "evento"
    __table_args__ = (
        Index("ix_evento_fecha_tipo", "fecha_hecho", "tipo"),
        Index("ix_evento_estado", "estado"),
        Index("ix_evento_responsable", "responsable_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    folio: Mapped[str] = mapped_column(String(20), unique=True)
    tipo: Mapped[Tipo] = mapped_column(_enum(Tipo, "tipo_evento"))
    subtipo: Mapped[str | None] = mapped_column(String(40))
    titulo: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text)
    referencia: Mapped[str | None] = mapped_column(String(500))
    fecha_hecho: Mapped[date] = mapped_column(Date)
    area_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("area.id"))
    solicitante_nombre: Mapped[str | None] = mapped_column(String(120))
    requiere_seguimiento: Mapped[bool] = mapped_column(Boolean, default=False)
    estado: Mapped[Estado] = mapped_column(_enum(Estado, "estado_evento"))
    prioridad: Mapped[Prioridad | None] = mapped_column(_enum(Prioridad, "prioridad_evento"))
    autor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"))
    responsable_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    busqueda: Mapped[str] = mapped_column(Text, default="", server_default="")

    area: Mapped[Area | None] = relationship()
    autor: Mapped[Usuario] = relationship(foreign_keys=[autor_id])
    responsable: Mapped[Usuario | None] = relationship(foreign_keys=[responsable_id])
