from sqlalchemy import text
from sqlalchemy.orm import Session


def siguiente_folio(db: Session, anio: int) -> str:
    """BIT-AAAA-NNNNN. El upsert es atómico en PostgreSQL (y en SQLite >= 3.35)."""
    n = db.execute(
        text(
            "INSERT INTO folio_secuencia (anio, ultimo) VALUES (:a, 1) "
            "ON CONFLICT (anio) DO UPDATE SET ultimo = folio_secuencia.ultimo + 1 "
            "RETURNING ultimo"
        ),
        {"a": anio},
    ).scalar_one()
    return f"BIT-{anio}-{n:05d}"
