"""Funciones de autenticación."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.rate_limit import login_ip_limiter, login_limiter
from app.core.security import crear_token, verificar_clave
from app.models import Usuario
from app.schemas import TokenOut
from app.services.historial import registrar_actividad, sincronizar_cuenta
from app.services.usuarios import a_salida


def login(db: Session, correo: str, clave: str, ip: str = "local") -> TokenOut:
    correo_norm = correo.strip().lower()
    llave_cuenta = f"acc:{ip}:{correo_norm}"
    llave_ip = f"ip:{ip}"
    login_limiter.verificar(llave_cuenta)
    login_ip_limiter.verificar(llave_ip)

    u = db.scalar(
        select(Usuario)
        .options(joinedload(Usuario.rol_custom))
        .where(Usuario.correo == correo_norm, Usuario.eliminado_en.is_(None))
    )
    if u is None or not u.activo or u.eliminado_en is not None or not verificar_clave(clave, u.clave_hash):
        login_limiter.registrar_fallo(llave_cuenta)
        login_ip_limiter.registrar_fallo(llave_ip)
        raise HTTPException(401, "Correo o clave incorrectos")

    login_limiter.limpiar(llave_cuenta)
    sincronizar_cuenta(db, u)
    registrar_actividad(
        db,
        u,
        accion="login_exitoso",
        entidad="sesion",
        entidad_id=str(u.id),
        titulo=f"Inicio de sesión de {u.nombre}",
        detalle=f"IP: {ip}",
    )
    db.commit()
    return TokenOut(token=crear_token(str(u.id), u.clave_hash), usuario=a_salida(u))
