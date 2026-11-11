import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.enums import Estado, Prioridad, Rol, Tipo


def _enum(e, nombre):
    # Guarda el valor ("en_proceso") y no el nombre Python.
    return Enum(e, name=nombre, values_callable=lambda x: [m.value for m in x])


def _ahora():
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str] = mapped_column(String(255), unique=True)
    rol: Mapped[Rol] = mapped_column(_enum(Rol, "rol"))
    clave_hash: Mapped[str] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)


class Area(Base):
    __tablename__ = "area"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class FolioSecuencia(Base):
    """Un contador por año. Garantiza folios únicos aun con altas simultáneas."""

    __tablename__ = "folio_secuencia"

    anio: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    ultimo: Mapped[int] = mapped_column(Integer, default=0)


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

    area: Mapped[Area | None] = relationship()
    autor: Mapped[Usuario] = relationship(foreign_keys=[autor_id])
    responsable: Mapped[Usuario | None] = relationship(foreign_keys=[responsable_id])
