"""Validadores reutilizables para esquemas Pydantic."""
import re


def validar_no_blanco(v: str | None) -> str | None:
    if v is None:
        return None
    limpio = v.strip()
    if not limpio:
        raise ValueError("El campo no puede estar vacío ni contener solo espacios")
    return limpio


def validar_clave_segura(v: str | None) -> str | None:
    if v is None:
        return None
    if len(v) < 8 or len(v) > 72:
        raise ValueError("La contraseña debe tener entre 8 y 72 caracteres")
    if any(ch.isspace() for ch in v):
        raise ValueError("La contraseña no puede contener espacios")
    if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
        raise ValueError("La contraseña debe incluir al menos una letra y un número")
    return v
