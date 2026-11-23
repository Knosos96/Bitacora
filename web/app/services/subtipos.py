"""Catálogo y administración de subtipos."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import tiene_permiso
from app.core.enums import SUBTIPOS, Permiso, Tipo
from app.models import Subtipo, Usuario
from app.schemas import SubtipoIn, SubtipoOut, SubtipoPatch

PREFIJO_ELIMINADO = "__del__:"


def _marca_eliminado(nombre: str) -> str:
    return f"{PREFIJO_ELIMINADO}{nombre}"


def vigentes(db: Session, tipo: Tipo) -> set[str]:
    filas_db = list(db.scalars(select(Subtipo).where(Subtipo.tipo == tipo)))
    eliminados = {
        f.nombre[len(PREFIJO_ELIMINADO):]
        for f in filas_db
        if f.nombre.startswith(PREFIJO_ELIMINADO)
    }
    validos = set(SUBTIPOS[tipo]) - eliminados
    for fila in filas_db:
        if fila.nombre.startswith(PREFIJO_ELIMINADO):
            continue
        (validos.add if fila.activo else validos.discard)(fila.nombre)
    return validos


def catalogo(db: Session, tipo: Tipo | None = None) -> list[dict]:
    """Todos los subtipos con su estado, incluidos los desactivados (excluye los eliminados)."""
    todas = list(db.scalars(select(Subtipo)))
    eliminados = {
        (f.tipo, f.nombre[len(PREFIJO_ELIMINADO):])
        for f in todas
        if f.nombre.startswith(PREFIJO_ELIMINADO)
    }
    ajustes = {
        (f.tipo, f.nombre): f.activo
        for f in todas
        if not f.nombre.startswith(PREFIJO_ELIMINADO)
    }
    filas = []
    for t in (tipo,) if tipo else Tipo:
        base_vigentes = {n for n in SUBTIPOS[t] if (t, n) not in eliminados}
        nombres = base_vigentes | {n for (tt, n) in ajustes if tt == t}
        for n in sorted(nombres):
            filas.append({"tipo": t, "nombre": n, "activo": ajustes.get((t, n), True), "base": n in SUBTIPOS[t]})
    return filas


def listar(db: Session, usuario: Usuario, tipo: Tipo | None = None, incluir_inactivos: bool = False):
    filas = catalogo(db, tipo)
    if not (incluir_inactivos and tiene_permiso(usuario, Permiso.gestionar_subtipos)):
        filas = [f for f in filas if f["activo"]]
    return filas


def crear(db: Session, datos: SubtipoIn) -> SubtipoOut:
    marca = db.get(Subtipo, (datos.tipo, _marca_eliminado(datos.nombre)))
    if marca:
        db.delete(marca)
        db.flush()
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


def eliminar(db: Session, tipo: Tipo, nombre: str) -> None:
    existe = any(f["nombre"] == nombre for f in catalogo(db, tipo))
    if not existe:
        raise HTTPException(404, "Subtipo no encontrado")
    fila = db.get(Subtipo, (tipo, nombre))
    if fila:
        db.delete(fila)
    if nombre in SUBTIPOS[tipo]:
        marca_key = _marca_eliminado(nombre)
        if not db.get(Subtipo, (tipo, marca_key)):
            db.add(Subtipo(tipo=tipo, nombre=marca_key, activo=False))
    db.commit()
