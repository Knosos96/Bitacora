"""Modelos de usuario y roles personalizados."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.enums import Rol
from app.models.common import _ahora, _enum


class RolPersonalizado(Base):
    """Rol creado por el jefe con permisos granulares."""

    __tablename__ = "rol_personalizado"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    descripcion: Mapped[str] = mapped_column(Text, default="")
    permisos: Mapped[list] = mapped_column(JSON, default=list)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str] = mapped_column(String(255), unique=True)
    rol: Mapped[Rol] = mapped_column(_enum(Rol, "rol"))
    clave_hash: Mapped[str] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
    eliminado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rol_custom_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rol_personalizado.id"), nullable=True)

    rol_custom: Mapped["RolPersonalizado | None"] = relationship(foreign_keys=[rol_custom_id])
