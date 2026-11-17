from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import requiere_rol, usuario_actual
from app.enums import SUBTIPOS, Rol, Tipo
from app.models import Subtipo, Usuario
from app.schemas import SubtipoIn, SubtipoOut, SubtipoPatch
from app.subtipos import catalogo

router = APIRouter(prefix="/subtipos", tags=["subtipos"])


@router.get("", response_model=list[SubtipoOut])
def listar_subtipos(
    tipo: Tipo | None = None,
    incluir_inactivos: bool = Query(False),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    filas = catalogo(db, tipo)
    if not (incluir_inactivos and usuario.rol in (Rol.encargado, Rol.jefe)):
        filas = [f for f in filas if f["activo"]]
    return filas


@router.post("", response_model=SubtipoOut, status_code=201)
def crear_subtipo(
    datos: SubtipoIn,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.encargado, Rol.jefe)),
):
    """CU-17. Agrega un subtipo a un tipo. Si existía desactivado, lo reactiva."""
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


@router.patch("/{tipo}/{nombre}", response_model=SubtipoOut)
def activar_o_desactivar(
    tipo: Tipo,
    nombre: str,
    datos: SubtipoPatch,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.encargado, Rol.jefe)),
):
    """Desactivar no altera los eventos que ya lo usan; solo deja de ofrecerse y de aceptarse en altas nuevas."""
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
