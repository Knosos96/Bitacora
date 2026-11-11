from fastapi import FastAPI

from app.routers import areas, auth, eventos, usuarios

app = FastAPI(
    title="Bitácora TI",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

for r in (auth.router, usuarios.router, areas.router, eventos.router):
    app.include_router(r, prefix="/api/v1")


@app.get("/api/v1/salud", tags=["salud"])
def salud():
    return {"ok": True}
