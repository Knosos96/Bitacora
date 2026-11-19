import uuid

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.enums import PERMISOS_BASE, Permiso, Rol
from app.models import Usuario
from app.security import leer_token

bearer = HTTPBearer(auto_error=False)


def usuario_actual(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if cred is None:
        raise HTTPException(401, "Falta el token")
    sub = leer_token(cred.credentials)
    if sub is None:
        raise HTTPException(401, "Token inválido o vencido")
    usuario = db.get(Usuario, uuid.UUID(sub))
    if usuario is None or not usuario.activo:
        raise HTTPException(401, "Usuario inactivo")
    return usuario


def permisos_de(usuario: Usuario) -> set[Permiso]:
    """Devuelve el conjunto de permisos efectivos del usuario.
    Si tiene un rol personalizado activo, usa sus permisos; si no, usa los del rol base."""
    if usuario.rol_custom_id and usuario.rol_custom and usuario.rol_custom.activo:
        return {Permiso(p) for p in usuario.rol_custom.permisos if p in Permiso._value2member_map_}
    return PERMISOS_BASE.get(usuario.rol, set())


def requiere_rol(*roles: Rol):
    def dependencia(u: Usuario = Depends(usuario_actual)) -> Usuario:
        if u.rol not in roles:
            raise HTTPException(409, {"codigo": "sin_permiso", "detalle": "Tu rol no permite esta acción"})
        return u

    return dependencia


def requiere_permiso(*permisos: Permiso):
    """Dependencia que verifica que el usuario tenga AL MENOS UNO de los permisos indicados
    (bien por su rol base o por su rol personalizado)."""
    def dependencia(u: Usuario = Depends(usuario_actual)) -> Usuario:
        efectivos = permisos_de(u)
        if not efectivos.intersection(permisos):
            raise HTTPException(409, {"codigo": "sin_permiso", "detalle": "Tu rol no permite esta acción"})
        return u

    return dependencia


# ---------------------------------------------------------------- Sprint 5: clave de API
import hashlib  # noqa: E402
import secrets  # noqa: E402
from dataclasses import dataclass  # noqa: E402

from fastapi import Header, Request  # noqa: E402

from app.models import ClaveApi, UsoClaveApi  # noqa: E402


def hash_clave_api(clave: str) -> str:
    # La clave es aleatoria y larga (no una contraseña elegida), por eso basta un hash rápido.
    return hashlib.sha256(clave.encode()).hexdigest()


def generar_clave_api() -> str:
    return "bti_" + secrets.token_urlsafe(32)


@dataclass
class Acceso:
    """Quién consulta: una persona con sesión o un programa con clave. Nunca ambos."""

    usuario: Usuario | None = None
    clave: ClaveApi | None = None


def acceso_lectura(
    request: Request,
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Acceso:
    """Solo para los GET de consulta (lista, ficha, resumen). Los demás endpoints siguen exigiendo sesión,
    así que una clave de API no puede escribir."""
    if x_api_key:
        clave = db.scalar(select(ClaveApi).where(ClaveApi.hash == hash_clave_api(x_api_key)))
        if clave is None or clave.revocada_en is not None:
            raise HTTPException(401, "Clave de API inválida o revocada")
        db.add(UsoClaveApi(clave_id=clave.id, metodo=request.method, ruta=request.url.path[:200]))
        db.commit()
        return Acceso(clave=clave)
    return Acceso(usuario=usuario_actual(cred, db))
