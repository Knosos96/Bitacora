import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, String, Text, Uuid, event
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db import Base
from app.enums import Estado, EstadoCompromiso, Prioridad, Rol, Tipo


class TSVector(TypeDecorator):
    """Tipo TSVECTOR para PostgreSQL con fallback a Text en SQLite (pruebas)."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(Text())


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
        Index("ix_evento_busqueda", "busqueda", postgresql_using="gin"),
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
    # Vector de texto completo PostgreSQL tsvector (con fallback a texto en SQLite para pruebas).
    # Reúne título, descripción, solicitante, referencia, notas y compromisos. Acelerado con índice GIN.
    busqueda: Mapped[str | None] = mapped_column(TSVector, nullable=True)

    area: Mapped[Area | None] = relationship()
    autor: Mapped[Usuario] = relationship(foreign_keys=[autor_id])
    responsable: Mapped[Usuario | None] = relationship(foreign_keys=[responsable_id])


class Seguimiento(Base):
    """Nota de seguimiento. Inmutable: no se edita ni se borra (ver el listener al final)."""

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


class Auditoria(Base):
    """Correcciones de la cabecera del evento: campo, valor anterior, valor nuevo, usuario y fecha."""

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


@event.listens_for(Seguimiento, "before_update")
def _nota_inmutable_update(*_):
    raise ValueError("Las notas de seguimiento no se editan; agrega otra nota.")


@event.listens_for(Seguimiento, "before_delete")
def _nota_inmutable_delete(*_):
    raise ValueError("Las notas de seguimiento no se eliminan.")
