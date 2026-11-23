import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

ALGORITMO = "HS256"


def hashear_clave(clave: str) -> str:
    return bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode()


def verificar_clave(clave: str, hash_: str) -> bool:
    try:
        return bcrypt.checkpw(clave.encode(), hash_.encode())
    except ValueError:
        return False


def huella_clave(clave_hash: str) -> str:
    """Huella corta del hash para invalidar sesiones previas cuando cambia la contraseña."""
    return hashlib.sha256(clave_hash.encode()).hexdigest()[:16]


def crear_token(usuario_id: str, clave_hash: str | None = None) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.token_horas)
    payload: dict = {"sub": usuario_id, "exp": exp}
    if clave_hash is not None:
        payload["ver"] = huella_clave(clave_hash)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITMO)


def leer_payload_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITMO])
        if not isinstance(payload, dict) or not payload.get("sub"):
            return None
        return payload
    except jwt.PyJWTError:
        return None


def leer_token(token: str) -> str | None:
    payload = leer_payload_token(token)
    return payload.get("sub") if payload else None
