from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def asegurar_esquema_sqlite() -> None:
    """Crea tablas nuevas y agrega columnas faltantes en instalaciones SQLite locales existentes."""
    if not settings.database_url.startswith("sqlite"):
        return
    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    with engine.begin() as conn:
        if insp.has_table("usuario"):
            cols = {c["name"] for c in insp.get_columns("usuario")}
            if "eliminado_en" not in cols:
                conn.execute(text("ALTER TABLE usuario ADD COLUMN eliminado_en DATETIME"))
        if insp.has_table("evento_origen"):
            cols = {c["name"] for c in insp.get_columns("evento_origen")}
            if "area_nombre" not in cols:
                conn.execute(text("ALTER TABLE evento_origen ADD COLUMN area_nombre VARCHAR(120)"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
