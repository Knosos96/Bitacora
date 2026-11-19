"""Compatibilidad: usar app.api.routes.usuarios."""
from app.api.routes.usuarios import *  # noqa: F401,F403
from app.api.routes.usuarios import router  # noqa: F401
