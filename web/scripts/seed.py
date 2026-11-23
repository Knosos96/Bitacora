"""Crea el primer jefe, el superusuario de auditoría y las áreas iniciales.
Uso: python -m scripts.seed jefe@correo.com "Nombre Jefe" "claveSegura123"
"""
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.core.enums import Rol
from app.core.security import hashear_clave
from app.models import Area, Usuario
from app.services.historial import sincronizar_cuenta, sincronizar_existentes

AREAS = ["Desarrollo TI", "Contabilidad", "Operaciones", "Mantenimiento", "Recursos Humanos"]


def main(correo: str, nombre: str, clave: str):
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if not db.scalar(select(Usuario).where(Usuario.correo == correo.lower())):
            u_jefe = Usuario(
                nombre=nombre, correo=correo.lower(), rol=Rol.jefe, clave_hash=hashear_clave(clave)
            )
            db.add(u_jefe)
            db.flush()
            sincronizar_cuenta(db, u_jefe)

        super_correo = settings.seed_super_correo.strip().lower()
        if super_correo and not db.scalar(select(Usuario).where(Usuario.correo == super_correo)):
            u_super = Usuario(
                nombre=settings.seed_super_nombre.strip(),
                correo=super_correo,
                rol=Rol.superusuario,
                clave_hash=hashear_clave(settings.seed_super_clave),
            )
            db.add(u_super)
            db.flush()
            sincronizar_cuenta(db, u_super)

        for n in AREAS:
            if not db.scalar(select(Area).where(Area.nombre == n)):
                db.add(Area(nombre=n))
        db.commit()
        sincronizar_existentes(db)
        print("Listo: jefe, superusuario y áreas iniciales creados.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
