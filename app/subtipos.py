"""Catálogo de subtipos: los iniciales (app.enums.SUBTIPOS) más los ajustes guardados en la tabla `subtipo`."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import SUBTIPOS, Tipo
from app.models import Subtipo


def vigentes(db: Session, tipo: Tipo) -> set[str]:
    validos = set(SUBTIPOS[tipo])
    for fila in db.scalars(select(Subtipo).where(Subtipo.tipo == tipo)):
        (validos.add if fila.activo else validos.discard)(fila.nombre)
    return validos


def catalogo(db: Session, tipo: Tipo | None = None) -> list[dict]:
    """Todos los subtipos con su estado, incluidos los desactivados."""
    ajustes = {(f.tipo, f.nombre): f.activo for f in db.scalars(select(Subtipo))}
    filas = []
    for t in (tipo,) if tipo else Tipo:
        nombres = set(SUBTIPOS[t]) | {n for (tt, n) in ajustes if tt == t}
        for n in sorted(nombres):
            filas.append({"tipo": t, "nombre": n, "activo": ajustes.get((t, n), True), "base": n in SUBTIPOS[t]})
    return filas
