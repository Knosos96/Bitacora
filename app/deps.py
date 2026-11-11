import uuid

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.enums import Rol
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


def requiere_rol(*roles: Rol):
    def dependencia(u: Usuario = Depends(usuario_actual)) -> Usuario:
        if u.rol not in roles:
            raise HTTPException(409, {"codigo": "sin_permiso", "detalle": "Tu rol no permite esta acción"})
        return u

    return dependencia
