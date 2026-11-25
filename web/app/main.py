"""Punto de entrada de la API FastAPI y la aplicación web."""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.db import asegurar_esquema_sqlite
from app.routers import ALL_ROUTERS

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

app = FastAPI(
    title="Bitácora TI",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)


@app.middleware("http")
async def cabeceras_seguridad(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if not request.url.path.startswith("/api/v1/docs"):
        response.headers.setdefault("Content-Security-Policy", CSP_POLICY)
    if request.url.path.startswith(("/api/v1/auth", "/api/v1/usuarios", "/api/v1/claves-api")):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


for router in ALL_ROUTERS:
    app.include_router(router, prefix="/api/v1")


if settings.database_url.startswith("sqlite:///") and settings.database_url != "sqlite://":
    asegurar_esquema_sqlite()


@app.get("/api/v1/salud", tags=["salud"])
def salud():
    return {"ok": True}


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if (TEMPLATES_DIR / "index.html").is_file():
    @app.get("/", include_in_schema=False)
    def web_index():
        return FileResponse(TEMPLATES_DIR / "index.html")
