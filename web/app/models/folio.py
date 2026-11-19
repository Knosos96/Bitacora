"""Secuencia anual de folios."""
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class FolioSecuencia(Base):
    """Un contador por año. Garantiza folios únicos aun con altas simultáneas."""

    __tablename__ = "folio_secuencia"

    anio: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    ultimo: Mapped[int] = mapped_column(Integer, default=0)
