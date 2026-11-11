"""Resetea la clave de un usuario.
Uso: python -m scripts.reset_clave correo nueva_clave
"""
import sys
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Usuario
from app.security import hashear_clave, verificar_clave

correo = sys.argv[1] if len(sys.argv) > 1 else "jefe@correo.com"
nueva_clave = sys.argv[2] if len(sys.argv) > 2 else "clave123"

db = SessionLocal()
usuarios = db.scalars(select(Usuario)).all()
print(f"Usuarios en BD ({len(usuarios)}):")
for u in usuarios:
    print(f"  - {u.correo}  activo={u.activo}")

u = db.scalar(select(Usuario).where(Usuario.correo == correo.lower()))
if u:
    u.clave_hash = hashear_clave(nueva_clave)
    db.commit()
    # verificar
    u2 = db.scalar(select(Usuario).where(Usuario.correo == correo.lower()))
    ok = verificar_clave(nueva_clave, u2.clave_hash)
    print(f"\nClave de '{correo}' reseteada a: '{nueva_clave}'  verificacion={ok}")
else:
    print(f"\nUsuario '{correo}' NO encontrado en la BD.")
db.close()
