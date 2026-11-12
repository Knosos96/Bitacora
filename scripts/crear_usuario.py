"""Crea un usuario en la base de datos con cualquier rol.
Uso: python -m scripts.crear_usuario correo@dominio.com "Nombre Apellido" "contraseña" [asistente|encargado|jefe]
"""
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.enums import Rol
from app.models import Usuario
from app.security import hashear_clave


def main(correo: str, nombre: str, clave: str, rol_str: str = "asistente"):
    rol_str = rol_str.lower()
    if rol_str not in Rol._value2member_map_:
        sys.exit(f"Rol no válido: '{rol_str}'. Opciones: {list(Rol._value2member_map_.keys())}")

    rol = Rol(rol_str)
    db = SessionLocal()
    correo = correo.strip().lower()
    if db.scalar(select(Usuario).where(Usuario.correo == correo)):
        db.close()
        sys.exit(f"El usuario con correo {correo} ya existe.")

    db.add(Usuario(nombre=nombre, correo=correo, rol=rol, clave_hash=hashear_clave(clave)))
    db.commit()
    db.close()
    print(f"Listo: usuario '{nombre}' ({correo}) creado con rol '{rol.value}'.")


if __name__ == "__main__":
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
