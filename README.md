# Bitácora TI — Sprint 1

## Puesta en marcha
1. `docker compose up -d`            # PostgreSQL local
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. `cp .env.example .env`           # cambia SECRET_KEY
5. `alembic revision --autogenerate -m "esquema inicial"`   # revisa el archivo generado
6. `alembic upgrade head`
7. `python -m scripts.seed jefe@correo.com "Nombre Jefe" "claveSegura123"`
8. `uvicorn app.main:app --reload`
9. Abre http://localhost:8000/api/v1/docs

## Pruebas
`pytest -q`   (usan SQLite en memoria; no necesitan PostgreSQL)

## Endpoints del Sprint 1
POST /api/v1/auth/login · GET /api/v1/auth/yo
POST/GET /api/v1/usuarios (jefe) · POST/GET /api/v1/areas
POST/GET /api/v1/eventos · GET /api/v1/eventos/{folio|uuid}

## Aplicación de escritorio (Tkinter)
Con la API corriendo (paso 8):
    python -m desktop.app
Pide servidor (por defecto http://localhost:8000), correo y clave. Muestra los eventos de hoy,
filtra por fecha y tipo, abre el detalle con doble clic y tiene el formulario de alta abajo.
En Linux puede hacer falta `sudo apt install python3-tk`.
