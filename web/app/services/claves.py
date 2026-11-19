"""Funciones de claves API."""
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import generar_clave_api, hash_clave_api
from app.models import ClaveApi, UsoClaveApi, Usuario, _ahora
from app.schemas import ClaveApiCreada, ClaveApiIn


def salida(db: Session, c: ClaveApi) -> dict:
    usos, ultimo = db.execute(
        select(func.count(), func.max(UsoClaveApi.creado_en)).where(UsoClaveApi.clave_id == c.id)
    ).one()
    return dict(
        id=c.id, nombre=c.nombre, prefijo=c.prefijo, creado_en=c.creado_en,
        revocada_en=c.revocada_en, ultimo_uso=ultimo, usos=usos,
    )


def crear(db: Session, datos: ClaveApiIn, jefe: Usuario) -> ClaveApiCreada:
    clave = generar_clave_api()
    c = ClaveApi(nombre=datos.nombre.strip(), prefijo=clave[:8], hash=hash_clave_api(clave), creada_por_id=jefe.id)
    db.add(c)
    db.commit()
    return ClaveApiCreada(**salida(db, c), clave=clave)


def listar(db: Session) -> list[dict]:
    filas = db.scalars(select(ClaveApi).order_by(ClaveApi.creado_en.desc())).all()
    return [salida(db, c) for c in filas]


def revocar(db: Session, clave_id: uuid.UUID) -> dict:
    c = db.get(ClaveApi, clave_id)
    if c is None:
        raise HTTPException(404, "Clave no encontrada")
    if c.revocada_en is None:
        c.revocada_en = _ahora()
        db.commit()
    return salida(db, c)
