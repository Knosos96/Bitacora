"""Modelo de área."""
import uuid

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Area(Base):
    __tablename__ = "area"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
