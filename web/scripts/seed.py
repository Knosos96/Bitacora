"""Crea el primer jefe y las áreas iniciales.
Uso: python -m scripts.seed jefe@correo.com "Nombre Jefe" "claveSegura123"
"""
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.enums import Rol
from app.models import Area, Usuario
from app.security import hashear_clave

AREAS = ["Desarrollo TI", "Contabilidad", "Operaciones", "Mantenimiento", "Recursos Humanos"]


def main(correo: str, nombre: str, clave: str):
    db = SessionLocal()
    if not db.scalar(select(Usuario).where(Usuario.correo == correo.lower())):
        db.add(Usuario(nombre=nombre, correo=correo.lower(), rol=Rol.jefe, clave_hash=hashear_clave(clave)))
    for n in AREAS:
        if not db.scalar(select(Area).where(Area.nombre == n)):
            db.add(Area(nombre=n))
    db.commit()
    print("Listo: jefe y áreas iniciales creados.")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
