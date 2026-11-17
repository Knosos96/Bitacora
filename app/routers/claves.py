import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import generar_clave_api, hash_clave_api, requiere_rol
from app.enums import Rol
from app.models import ClaveApi, UsoClaveApi, Usuario, _ahora
from app.schemas import ClaveApiCreada, ClaveApiIn, ClaveApiOut

router = APIRouter(prefix="/claves-api", tags=["claves-api"])


def _salida(db: Session, c: ClaveApi) -> dict:
    usos, ultimo = db.execute(
        select(func.count(), func.max(UsoClaveApi.creado_en)).where(UsoClaveApi.clave_id == c.id)
    ).one()
    return dict(id=c.id, nombre=c.nombre, prefijo=c.prefijo, creado_en=c.creado_en, revocada_en=c.revocada_en,
                ultimo_uso=ultimo, usos=usos)


@router.post("", response_model=ClaveApiCreada, status_code=201)
def crear_clave(datos: ClaveApiIn, db: Session = Depends(get_db), jefe: Usuario = Depends(requiere_rol(Rol.jefe))):
    """CU-18. La clave en claro se muestra una sola vez; después solo existe su hash."""
    clave = generar_clave_api()
    c = ClaveApi(nombre=datos.nombre.strip(), prefijo=clave[:8], hash=hash_clave_api(clave), creada_por_id=jefe.id)
    db.add(c)
    db.commit()
    return ClaveApiCreada(**_salida(db, c), clave=clave)


@router.get("", response_model=list[ClaveApiOut])
def listar_claves(db: Session = Depends(get_db), _: Usuario = Depends(requiere_rol(Rol.jefe))):
    filas = db.scalars(select(ClaveApi).order_by(ClaveApi.creado_en.desc())).all()
    return [_salida(db, c) for c in filas]


@router.delete("/{clave_id}", response_model=ClaveApiOut)
def revocar_clave(clave_id: uuid.UUID, db: Session = Depends(get_db), _: Usuario = Depends(requiere_rol(Rol.jefe))):
    """Corta el acceso de inmediato. La clave no se borra: queda su historial de uso."""
    c = db.get(ClaveApi, clave_id)
    if c is None:
        raise HTTPException(404, "Clave no encontrada")
    if c.revocada_en is None:
        c.revocada_en = _ahora()
        db.commit()
    return _salida(db, c)
