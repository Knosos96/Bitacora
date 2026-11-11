from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

ALGORITMO = "HS256"


def hashear_clave(clave: str) -> str:
    return bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode()


def verificar_clave(clave: str, hash_: str) -> bool:
    try:
        return bcrypt.checkpw(clave.encode(), hash_.encode())
    except ValueError:
        return False


def crear_token(usuario_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.token_horas)
    return jwt.encode({"sub": usuario_id, "exp": exp}, settings.secret_key, algorithm=ALGORITMO)


def leer_token(token: str) -> str | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITMO])["sub"]
    except jwt.PyJWTError:
        return None
