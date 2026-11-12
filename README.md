# Bitácora TI — Sprints 1 y 2

API FastAPI + PostgreSQL 16 + app de escritorio (Tkinter).
Sprint 1: auth, usuarios, áreas, eventos y folios. Sprint 2: seguimiento, estados, notas, compromisos y pendientes.

## Con Docker (recomendado)
```bash
cp .env.example .env        # cambia SECRET_KEY y SEED_JEFE_CLAVE
docker compose up -d --build
```
Al arrancar, el contenedor `api` espera a PostgreSQL, ejecuta `alembic upgrade head` y, si `SEED_JEFE_*` están
definidos, crea el jefe y las áreas iniciales (es idempotente: repetirlo no duplica nada).
Docs de la API: http://localhost:8000/api/v1/docs

Comandos útiles:
```bash
docker compose logs -f api                       # ver el log
docker compose exec api python -m scripts.crear_usuario usuario@correo.com "Nombre" "clave123" asistente
docker compose exec db psql -U bitacora         # consola SQL
docker compose down                              # apagar (los datos quedan en el volumen pgdata)
docker compose down -v                           # apagar Y borrar la base
docker compose exec db pg_dump -U bitacora bitacora > respaldo.sql   # respaldo
```

## Sin Docker para la API (solo la base en Docker)
```bash
docker compose up -d db
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m scripts.seed jefe@correo.com "Nombre Jefe" "claveSegura123"
uvicorn app.main:app --reload
```

## Migraciones
Ya vienen escritas: `0001` (sprint 1) y `0002` (sprint 2: `seguimiento`, `compromiso` y un trigger que impide
editar o borrar notas). Para un cambio nuevo: edita `app/models.py` y
`alembic revision --autogenerate -m "descripcion"`, revisa el archivo y `alembic upgrade head`.
Si ya tenías una base creada con el Sprint 1 sin Alembic, bórrala (`docker compose down -v`) y empieza de nuevo.

## Pruebas
`pytest -q` (SQLite en memoria; no necesitan PostgreSQL ni Docker).

## Aplicación de escritorio
Con la API corriendo: `python -m desktop.app` (servidor por defecto http://localhost:8000).
Doble clic en un evento abre la ficha: cambiar estado, activar/quitar seguimiento, notas y compromisos.
El botón **Pendientes** muestra lo abierto y los compromisos (con filtro de vencidos).
En Linux: `sudo apt install python3-tk`.

## Endpoints nuevos del Sprint 2
| Método y ruta | Caso de uso | Quién |
| --- | --- | --- |
| `PATCH /eventos/{folio}` | CU-04 activar/quitar seguimiento · CU-05 responsable y prioridad | activar: todos · quitar y asignar: encargado/jefe |
| `POST /eventos/{folio}/estado` | CU-08 cambiar estado · CU-09 cerrar | ver reglas |
| `GET/POST /eventos/{folio}/seguimientos` | CU-07 notas (inmutables) | todos |
| `GET/POST /eventos/{folio}/compromisos` | CU-06 | todos |
| `PATCH /compromisos/{id}` | cumplir o cancelar | responsable, encargado, jefe |
| `GET /pendientes?solo_mios&solo_vencidos` | CU-15 | asistente ve lo suyo; encargado/jefe todo |
| `GET /eventos/{folio}?incluir=seguimientos,compromisos` | detalle completo | todos |

### Reglas de estado
- `informativo` solo sale activando el seguimiento (queda `abierto`, responsable = quien lo activa, prioridad media).
- `abierto → en_proceso | en_espera | resuelto | cancelado`; `en_proceso ↔ en_espera`; `resuelto → en_proceso | cerrado`.
- `cerrado` y `cancelado` son finales (reabrir llega en el Sprint 6).
- El asistente solo avanza sus eventos (autor o responsable) hasta `resuelto`. Cancelar y cerrar: encargado/jefe.
- Atajo: encargado/jefe cierran desde `en_proceso`/`en_espera` con nota de cierre. `en_espera` exige nota.
- Cerrar o cancelar con compromisos pendientes responde `409 compromisos_pendientes`, salvo que se envíe
  `resolver_compromisos: "cumplir" | "cancelar"` (así se concilia el CU-09 con el criterio de listo del Sprint 2).
- Cada cambio escribe una nota automática; la nota de la persona se guarda aparte.
- Errores de dominio: `409` con `{"codigo": ..., "detalle": ...}` (`sin_permiso`, `transicion_invalida`,
  `sin_seguimiento`, `evento_cerrado`, `compromisos_pendientes`).
