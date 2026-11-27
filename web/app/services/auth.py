"""Funciones de autenticación."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.rate_limit import login_ip_limiter, login_limiter
from app.core.security import crear_token, hashear_clave, verificar_clave
from app.models import Usuario
from app.schemas import PerfilPatch, TokenOut
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


def actualizar_perfil(db: Session, usuario: Usuario, datos: PerfilPatch) -> TokenOut:
    """Permite al usuario autenticado actualizar su nombre, correo y/o contraseña confirmando su clave actual."""
    if not verificar_clave(datos.clave_actual, usuario.clave_hash):
        raise HTTPException(401, "La contraseña actual es incorrecta")

    cambios: list[str] = []
    if datos.nombre is not None:
        nuevo_nombre = datos.nombre.strip()
        if nuevo_nombre != usuario.nombre:
            usuario.nombre = nuevo_nombre
            cambios.append("nombre")

    if datos.correo is not None:
        nuevo_correo = str(datos.correo).strip().lower()
        if nuevo_correo != usuario.correo:
            ocupado = db.scalar(
                select(Usuario).where(
                    Usuario.correo == nuevo_correo,
                    Usuario.eliminado_en.is_(None),
                    Usuario.id != usuario.id,
                )
            )
            if ocupado is not None:
                raise HTTPException(400, "Ya existe otro usuario con ese correo")
            prev_eliminado = db.scalar(
                select(Usuario).where(
                    Usuario.correo == nuevo_correo,
                    Usuario.eliminado_en.is_not(None),
                    Usuario.id != usuario.id,
                )
            )
            if prev_eliminado is not None:
                prev_eliminado.correo = f"{nuevo_correo}#del#{prev_eliminado.id}"
                db.flush()
            usuario.correo = nuevo_correo
            cambios.append("correo")

    if datos.clave_nueva is not None:
        usuario.clave_hash = hashear_clave(datos.clave_nueva)
        cambios.append("clave_actualizada")

    if not cambios:
        raise HTTPException(400, "No se detectaron cambios para guardar")

    sincronizar_cuenta(db, usuario)
    registrar_actividad(
        db,
        usuario,
        accion="perfil_actualizado",
        entidad="usuario",
        entidad_id=str(usuario.id),
        titulo=f"{usuario.nombre} ({usuario.correo})",
        detalle="Actualización propia: " + ", ".join(cambios),
    )
    db.commit()
    refrescado = db.scalar(
        select(Usuario).options(joinedload(Usuario.rol_custom)).where(Usuario.id == usuario.id)
    )
    return TokenOut(token=crear_token(str(refrescado.id), refrescado.clave_hash), usuario=a_salida(refrescado))
