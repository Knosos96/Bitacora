"""Modelos de claves API y su uso."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.common import _ahora


class ClaveApi(Base):
    """Clave de solo lectura. Solo se guarda su hash (sha256)."""

    __tablename__ = "clave_api"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(120))
    prefijo: Mapped[str] = mapped_column(String(12))
    hash: Mapped[str] = mapped_column(String(64), unique=True)
    creada_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
    revocada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UsoClaveApi(Base):
    """Registro de acceso: fecha, clave y ruta."""

    __tablename__ = "uso_clave_api"
    __table_args__ = (Index("ix_uso_clave", "clave_id", "creado_en"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    clave_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clave_api.id"))
    metodo: Mapped[str] = mapped_column(String(8))
    ruta: Mapped[str] = mapped_column(String(200))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
