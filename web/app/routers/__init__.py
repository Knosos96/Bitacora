"""Routers modulares de la API REST."""
from app.routers import (
    areas,
    auth,
    claves,
    compromisos,
    eventos,
    kpi,
    pendientes,
    roles,
    subtipos,
    superadmin,
    usuarios,
)

ALL_ROUTERS = (
    auth.router,
    usuarios.router,
    areas.router,
    eventos.router,
    compromisos.router,
    pendientes.router,
    kpi.router,
    claves.router,
    subtipos.router,
    roles.router,
    superadmin.router,
)

__all__ = [
    "ALL_ROUTERS",
    "areas",
    "auth",
    "claves",
    "compromisos",
    "eventos",
    "kpi",
    "pendientes",
    "roles",
    "subtipos",
    "superadmin",
    "usuarios",
]
