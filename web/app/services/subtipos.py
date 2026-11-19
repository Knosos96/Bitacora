"""Catálogo y administración de subtipos."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import SUBTIPOS, Rol, Tipo
from app.models import Subtipo, Usuario
from app.schemas import SubtipoIn, SubtipoOut, SubtipoPatch


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


def listar(db: Session, usuario: Usuario, tipo: Tipo | None = None, incluir_inactivos: bool = False):
    filas = catalogo(db, tipo)
    if not (incluir_inactivos and usuario.rol in (Rol.encargado, Rol.jefe)):
        filas = [f for f in filas if f["activo"]]
    return filas


def crear(db: Session, datos: SubtipoIn) -> SubtipoOut:
    existente = db.get(Subtipo, (datos.tipo, datos.nombre))
    ya_activo = any(f["nombre"] == datos.nombre and f["activo"] for f in catalogo(db, datos.tipo))
    if ya_activo:
        raise HTTPException(400, "Ese subtipo ya existe")
    if existente:
        existente.activo = True
    else:
        db.add(Subtipo(tipo=datos.tipo, nombre=datos.nombre, activo=True))
    db.commit()
    return SubtipoOut(tipo=datos.tipo, nombre=datos.nombre, activo=True, base=datos.nombre in SUBTIPOS[datos.tipo])


def activar(db: Session, tipo: Tipo, nombre: str, datos: SubtipoPatch) -> SubtipoOut:
    existe = any(f["nombre"] == nombre for f in catalogo(db, tipo))
    if not existe:
        raise HTTPException(404, "Subtipo no encontrado")
    fila = db.get(Subtipo, (tipo, nombre))
    if fila:
        fila.activo = datos.activo
    else:
        db.add(Subtipo(tipo=tipo, nombre=nombre, activo=datos.activo))
    db.commit()
    return SubtipoOut(tipo=tipo, nombre=nombre, activo=datos.activo, base=nombre in SUBTIPOS[tipo])
