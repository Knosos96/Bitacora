# Bitácora TI — Sprints 1 a 4

API FastAPI + PostgreSQL 16 + app de escritorio (Tkinter).
Sprint 1: auth, usuarios, áreas, eventos y folios. Sprint 2: seguimiento, estados, notas, compromisos y pendientes.
Sprint 3: búsqueda de texto, filtros, historial y corrección con auditoría. Sprint 4: tablero con K1 a K12.

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
Ya vienen escritas: `0001` (sprint 1), `0002` (sprint 2: `seguimiento`, `compromiso` y un trigger que impide
editar o borrar notas) y `0003` (sprint 3: vector de búsqueda con PostgreSQL `tsvector`, índice `GIN` y tabla `auditoria`;
rellena la búsqueda de los eventos que ya existían). Para un cambio nuevo: edita `app/models.py` y
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

## Sprint 3 — Encontrar lo que se dijo
`GET /eventos` ahora acepta: `q` (texto o folio), `desde`, `hasta`, `tipo`, `estado`, `area_id`, `responsable_id`,
`seguimiento=con|sin`, `vencidos=true`, `page`, `page_size`. Sin fechas ni filtros sigue siendo la pantalla **Hoy**;
con texto, estado, área, responsable, seguimiento o vencidos y sin fechas, busca en todo el histórico.

- **Cómo busca:** en PostgreSQL usa búsqueda de texto completo con `tsvector` y diccionario `spanish` (`plainto_tsquery`)
  indexado mediante GIN. Reúne título, descripción, solicitante, referencia, notas y compromisos. Todas las palabras
  deben aparecer, en cualquier orden y campo. El lematizador en español maneja plurales y acentos automáticamente
  (`prestamo` encuentra "Préstamo"; `licencias` encuentra "licencia"). Las notas automáticas de cambio de estado no cuentan.
- **Fragmento:** cada resultado trae `fragmento` con el campo y el trozo de texto donde coincidió.
- **Folio:** `q=BIT-2026-00041` abre ese evento.
- **Historial:** `GET /eventos/{folio}?incluir=seguimientos,compromisos,auditoria`.
- **Corregir cabecera (CU-23):** `PATCH /eventos/{folio}` con `titulo`, `descripcion`, `referencia`, `solicitante_nombre`,
  `fecha_hecho`, `area_id`, `tipo`, `subtipo`. El autor corrige el mismo día; después, encargado o jefe. Cada cambio guarda
  campo, valor anterior, valor nuevo, usuario y fecha. `null` limpia referencia, solicitante, subtipo y área.

## Sprint 4 — Tablero del jefe
Solo encargado y jefe (el asistente recibe 403). Solo lectura.
- `GET /kpi?desde=&hasta=` — K1 a K12. Sin fechas, la semana en curso (lunes a domingo).
- `GET /kpi/{K1..K12}?desde=&hasta=&clave=` — la lista de eventos o compromisos que explica el número.
  `clave` afina: tipo (K1, K5), `con`/`sin` (K2), `a_tiempo`/`fuera` (K7), responsable o `sin` (K9), área (K10).

| | Indicador | Cómo se calcula |
| --- | --- | --- |
| K1 | Volumen por tipo | eventos con `fecha_hecho` en el rango |
| K2 | Con seguimiento vs informativos | ídem |
| K3 | Stock abierto | seguimiento activo en abierto, en_proceso o en_espera con `fecha_hecho` en el rango |
| K4 | Resueltos sin cerrar | estado `resuelto` con `fecha_hecho` en el rango |
| K5 | Tiempo medio de atención | horas entre registro y cierre; cerrados con `fecha_hecho` en el rango; por tipo; sin informativos |
| K6 | Cerrados en el rango | cierres ocurridos dentro del rango |
| K7 | Cumplimiento | % de compromisos con fecha límite en el rango cumplidos a más tardar ese día; los cancelados no cuentan |
| K8 | Vencidos en el rango | compromisos pendientes con fecha límite en el rango vencidos (fecha anterior a hoy) |
| K9 | Carga por persona | stock abierto en el rango por responsable (el valor es la carga máxima) |
| K10 | Áreas de origen | las 5 áreas con más eventos en el rango |
| K11 | Antigüedad máxima | días del evento abierto más viejo dentro del rango |
| K12 | Incidencias | incidencias en el rango |

Todos los indicadores (K1 a K12) dependen del rango de fechas consultado. Cuando no hay datos, el valor es `null` (la app muestra "sin datos").
En la app de escritorio: botón **Búsqueda…**, botón **Tablero** (encargado/jefe) y un aviso rojo en la pantalla principal con los compromisos vencidos.
