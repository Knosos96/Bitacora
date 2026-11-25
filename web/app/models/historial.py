"""Modelos de historial inmutable para el portal de Superusuario."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.common import _ahora


class CuentaHistorica(Base):
    """Registro histórico permanente de todas las cuentas creadas (activas, inactivas y eliminadas)."""

    __tablename__ = "cuenta_historica"
    __table_args__ = (Index("ix_cuenta_hist_estado", "estado", "creado_en"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str] = mapped_column(String(255), index=True)
    rol: Mapped[str] = mapped_column(String(40))
    rol_custom_nombre: Mapped[str | None] = mapped_column(String(80))
    estado: Mapped[str] = mapped_column(String(20), default="activa")  # activa | inactiva | eliminada
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
    eliminado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    eliminado_por_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    eliminado_por_nombre: Mapped[str | None] = mapped_column(String(120))
    eliminado_por_correo: Mapped[str | None] = mapped_column(String(255))


class EventoOrigen(Base):
    """Preserva al autor y responsable originales de cada evento aunque la cuenta sea eliminada."""

    __tablename__ = "evento_origen"

    evento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evento.id", ondelete="CASCADE"), primary_key=True)
    autor_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    autor_nombre: Mapped[str] = mapped_column(String(120))
    autor_correo: Mapped[str] = mapped_column(String(255))
    responsable_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    responsable_nombre: Mapped[str | None] = mapped_column(String(120))
    responsable_correo: Mapped[str | None] = mapped_column(String(255))
    area_nombre: Mapped[str | None] = mapped_column(String(120))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)


class ActividadBitacora(Base):
    """Bitácora cronológica inmutable de todas las acciones del sistema."""

    __tablename__ = "actividad_bitacora"
    __table_args__ = (
        Index("ix_actividad_actor_fecha", "actor_id", "creado_en"),
        Index("ix_actividad_entidad_fecha", "entidad", "creado_en"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    actor_nombre: Mapped[str] = mapped_column(String(120))
    actor_correo: Mapped[str] = mapped_column(String(255))
    actor_rol: Mapped[str] = mapped_column(String(40))
    accion: Mapped[str] = mapped_column(String(60), index=True)
    entidad: Mapped[str] = mapped_column(String(40))
    entidad_id: Mapped[str | None] = mapped_column(String(64))
    folio: Mapped[str | None] = mapped_column(String(30), index=True)
    titulo: Mapped[str | None] = mapped_column(String(250))
    detalle: Mapped[str] = mapped_column(Text, default="")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora, index=True)
