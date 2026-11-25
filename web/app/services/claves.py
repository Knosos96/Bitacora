"""Funciones de claves API."""
import uuid

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.deps import generar_clave_api, hash_clave_api
from app.models import ClaveApi, UsoClaveApi, Usuario, _ahora
from app.schemas import ClaveApiCreada, ClaveApiIn
from app.services.historial import registrar_actividad


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
    db.flush()
    registrar_actividad(db, jefe, "clave_api_creada", "clave_api", str(c.id), titulo=c.nombre, detalle=f"Prefijo: {c.prefijo}")
    db.commit()
    return ClaveApiCreada(**salida(db, c), clave=clave)


def listar(db: Session) -> list[dict]:
    filas = db.scalars(select(ClaveApi).order_by(ClaveApi.creado_en.desc())).all()
    return [salida(db, c) for c in filas]


def revocar(db: Session, clave_id: uuid.UUID, actor: Usuario | None = None) -> dict:
    c = db.get(ClaveApi, clave_id)
    if c is None:
        raise HTTPException(404, "Clave no encontrada")
    if c.revocada_en is None:
        c.revocada_en = _ahora()
        if actor is not None:
            registrar_actividad(db, actor, "clave_api_revocada", "clave_api", str(c.id), titulo=c.nombre)
        db.commit()
    return salida(db, c)


def eliminar(db: Session, clave_id: uuid.UUID, actor: Usuario | None = None) -> None:
    c = db.get(ClaveApi, clave_id)
    if c is None:
        raise HTTPException(404, "Clave no encontrada")
    nombre = c.nombre
    prefijo = c.prefijo
    usos = db.scalar(select(func.count()).select_from(UsoClaveApi).where(UsoClaveApi.clave_id == clave_id)) or 0
    db.execute(delete(UsoClaveApi).where(UsoClaveApi.clave_id == clave_id))
    if actor is not None:
        registrar_actividad(
            db,
            actor,
            "clave_api_eliminada",
            "clave_api",
            str(clave_id),
            titulo=nombre,
            detalle=f"Prefijo: {prefijo} · Usos históricos registrados: {usos}",
        )
    db.delete(c)
    db.commit()
