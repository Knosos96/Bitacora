"""Compatibilidad: usar app.api.routes.auth."""
from app.api.routes.auth import *  # noqa: F401,F403
from app.api.routes.auth import router  # noqa: F401
