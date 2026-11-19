from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    areas, auth, claves, compromisos, eventos, kpi, pendientes, roles, subtipos, usuarios,
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(
    title="Bitácora TI",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

for r in (auth.router, usuarios.router, areas.router, eventos.router, compromisos.router,
          pendientes.router, kpi.router, claves.router, subtipos.router, roles.router):
    app.include_router(r, prefix="/api/v1")


@app.get("/api/v1/salud", tags=["salud"])
def salud():
    return {"ok": True}


if WEB_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

    @app.get("/", include_in_schema=False)
    def web_index():
        return FileResponse(WEB_DIR / "index.html")
