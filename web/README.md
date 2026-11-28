# Bitácora TI — Sprints 1 a 6

API FastAPI + PostgreSQL 16 + app de escritorio (Tkinter).
Sprint 1: auth, usuarios, áreas, eventos y folios. Sprint 2: seguimiento, estados, notas, compromisos y pendientes.
Sprint 3: búsqueda de texto, filtros, historial y corrección con auditoría. Sprint 4: tablero con K1 a K12.
Sprint 5: API de solo lectura con claves. Sprint 6: reabrir, exportar CSV, administración, respaldos y semana piloto.

## Con Docker (recomendado)
```bash
cp .env.example .env        # cambia SECRET_KEY y SEED_JEFE_CLAVE
docker compose up -d --build
```
Al arrancar, el contenedor `api` espera a PostgreSQL, ejecuta `alembic upgrade head` y, si `SEED_JEFE_*` están
definidos, crea el jefe y las áreas iniciales (es idempotente: repetirlo no duplica nada).
App web (misma API): http://localhost:8000/  
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
editar o borrar notas) `0003` (sprint 3: texto de búsqueda con índice `pg_trgm` y tabla `auditoria`;
rellena la búsqueda de los eventos que ya existían) y `0004` (sprints 5 y 6: claves de API, su registro de uso y ajustes de subtipos). Para un cambio nuevo: edita el módulo correspondiente en `app/models/` y
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

- **Cómo busca:** cada evento guarda un texto normalizado (minúsculas, sin acentos) con título, descripción,
  solicitante, referencia, notas y compromisos. Todas las palabras deben aparecer, en cualquier orden y campo.
  `prestamo` encuentra "Préstamo"; `licencias` encuentra "licencia". Las notas automáticas de cambio de estado no cuentan.
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
| K3 | Stock abierto | seguimiento activo en abierto, en_proceso o en_espera (hoy) |
| K4 | Resueltos sin cerrar | estado `resuelto` (hoy) |
| K5 | Tiempo medio de atención | horas entre registro y cierre; cerrados con `fecha_hecho` en el rango; por tipo; sin informativos |
| K6 | Cerrados en el rango | cierres ocurridos dentro del rango |
| K7 | Cumplimiento | % de compromisos con fecha límite en el rango cumplidos a más tardar ese día; los cancelados no cuentan |
| K8 | Vencidos ahora | compromisos pendientes con fecha límite anterior a hoy |
| K9 | Carga por persona | stock abierto por responsable (el valor es la carga máxima) |
| K10 | Áreas de origen | las 5 áreas con más eventos en el rango |
| K11 | Antigüedad máxima | días del evento abierto más viejo |
| K12 | Incidencias | incidencias en el rango |

K3, K4, K8, K9 y K11 son del momento y no dependen del rango. Cuando no hay datos, el valor es `null` (la app muestra "sin datos").
En la app de escritorio: botón **Búsqueda…**, botón **Tablero** (encargado/jefe) y un aviso rojo en la pantalla principal con los compromisos vencidos.

## Sprint 5 — API para otro programa
Un programa externo consulta con una **clave de solo lectura** en el encabezado `X-API-Key`. La clave solo funciona en tres
GET; en cualquier otro endpoint responde 401, así que no puede escribir ni ver tablero, pendientes ni usuarios.

| Endpoint | Con clave |
| --- | --- |
| `GET /eventos` | `desde` y `hasta` **obligatorios**; filtros `tipo`, `estado`, `q`, `area_id`, `page`, `page_size` (máx. 200) |
| `GET /eventos/{folio o id}?incluir=seguimientos,compromisos` | `auditoria` no está disponible |
| `GET /eventos/resumen?desde=&hasta=&tipo=` | total y conteo por tipo |

Errores: `401` clave inexistente o revocada · `400` rango invertido, de más de 366 días, o sin `desde`/`hasta` · `404` evento inexistente.
Sin resultados es `200` con lista vacía.

Gestión de claves (solo el **jefe**):
- `POST /claves-api {"nombre": "..."}` → devuelve la clave en claro **una sola vez**; después solo existe su hash (sha256).
- `GET /claves-api` → nombre, prefijo, creación, último uso, número de usos, si está revocada.
- `DELETE /claves-api/{id}` → revoca: corta el acceso de inmediato y conserva el historial.
- Cada consulta con clave guarda fecha, clave, método y ruta. **No** guarda el cuerpo ni los parámetros.

```bash
curl -H "X-API-Key: bti_..." "http://localhost:8000/api/v1/eventos?desde=2026-11-09&hasta=2026-11-13&tipo=solicitud"
```
La especificación OpenAPI está en `/api/v1/openapi.json`; `tests/test_sprint5.py::test_contrato_openapi` verifica que coincida con lo que responde.

## Sprint 6 — Uso diario real
- **Reabrir (CU-10):** `POST /eventos/{folio}/estado {"estado":"abierto","nota":"motivo"}` sobre un evento cerrado. Solo encargado o jefe;
  el motivo es obligatorio; el evento vuelve a K3 y su `cerrado_en` se limpia. Un cancelado no se reabre.
- **Exportar CSV (CU-22):** `GET /eventos/exportar` con los mismos filtros que la lista, sin paginar (máx. 20 000 filas).
  Solo encargado y jefe. UTF-8 con BOM (Excel respeta los acentos) y los textos que empiezan con `= + - @` se neutralizan para evitar inyección de fórmulas.
- **Usuarios (CU-16, jefe):** `PATCH /usuarios/{id}` cambia nombre y rol, desactiva/reactiva y restablece la clave. Un usuario inactivo no entra
  ni puede ser responsable, pero su nombre queda en el historial. Siempre debe quedar al menos un jefe activo (`409 ultimo_jefe`).
- **Áreas (CU-17):** `PATCH /areas/{id}` renombra o desactiva; `GET /areas?incluir_inactivas=true` (encargado/jefe). Los eventos viejos conservan su área.
- **Subtipos (CU-17):** `GET/POST /subtipos`, `PATCH /subtipos/{tipo}/{nombre}`. Los de fábrica se pueden desactivar y se pueden agregar nuevos
  (minúsculas, sin espacios). Desactivar no altera eventos existentes.
- **Respaldos:** `./scripts/respaldo.sh` (conserva los últimos 14), `./scripts/restaurar.sh archivo [base]` (restaura en una base *nueva*),
  y `./scripts/ensayo_restauracion.sh`, que respalda, restaura en una base temporal y compara los conteos de cada tabla.
  Respaldo automático diario: `docker compose --profile respaldo up -d` (deja los archivos en `./respaldos`).
- **Semana piloto:** `PILOTO.md` trae la guía; `tests/test_piloto.py` es el mismo guion automatizado.
- **Escritorio:** botón **Administración** (usuarios y claves de API solo para el jefe), **Exportar CSV** dentro de Búsqueda,
  y reabrir desde la ficha de un evento cerrado.

## Permisos, en una tabla
| Acción | Asistente | Encargado | Jefe |
| --- | :-: | :-: | :-: |
| Registrar, buscar, notas, compromisos, pendientes (los suyos) | ✔ | ✔ | ✔ |
| Avanzar sus eventos hasta `resuelto` | ✔ | ✔ | ✔ |
| Cerrar, cancelar, reabrir, asignar responsable | | ✔ | ✔ |
| Corregir cabecera de eventos ajenos o de días anteriores | | ✔ | ✔ |
| Tablero y exportar CSV | | ✔ | ✔ |
| Áreas y subtipos | | ✔ | ✔ |
| Usuarios y claves de API | | | ✔ |

# ZGROUP · Bitácora TI (Versión Web Avanzada con Superusuario)

Sistema web de registro, seguimiento, indicadores KPI, auditoría documental e integración API de incidencias y eventos operativos de TI, construido con **FastAPI**, **PostgreSQL 16**, **Alembic**, **Vanilla JS modular (ES Modules)** y **CSS ITCSS**, con identidad corporativa **ZGROUP**.

> La versión activa y completa del sistema vive en la carpeta [`web/`](./web). *(Los archivos sueltos de la raíz `app/` y `desktop/` se mantienen únicamente como referencia histórica del Sprint 1).*

---

## Características principales

### Operación diaria y gestión (`Asistente`, `Encargado`, `Jefe` y `Roles personalizados`)
- **Hoy (`#/`)**: registro de eventos e incidencias con folios anuales únicos (`BIT-AAAA-NNNNN`), área de origen, solicitante, subtipos configurables y filtros diarios.
- **Detalle y seguimiento**: notas de seguimiento inmutables (protegidas con trigger en PostgreSQL `seguimiento_inmutable`), compromisos con fecha límite y detección de vencidos, transiciones de estado y corrección de cabecera con auditoría de cambios (`antes → después`).
- **Pendientes (`#/pendientes`)**: vista consolidada de eventos abiertos y compromisos activos/vencidos.
- **Búsqueda histórica (`#/busqueda`)**: búsqueda normalizada sin acentos por texto, folio, tipo, estado, seguimiento o fechas, con exportación **CSV** protegida contra inyección de fórmulas (`= + - @`).
- **Tablero KPI (`#/tablero`)**: 12 indicadores (`K1`–`K12`) con desglose por tarjeta y rango de fechas.
- **Administración (`#/admin`)**: gestión (crear, editar, filtrar, activar/desactivar y eliminar) de **Áreas**, **Subtipos**, **Usuarios**, **Roles personalizados** granulares y **Claves API** (`X-API-Key` de solo lectura).
- **Mi perfil (`#/perfil`)**: cambio de nombre, correo y contraseña propios confirmando clave actual, con rotación automática de sesión JWT.

### Portal exclusivo de Superusuario (`#/super/*`)
- **Preservación histórica sin cascada**: la eliminación de cuentas operativas por el Jefe es lógica (`eliminado_en`), conservando intactos eventos, notas, compromisos, auditoría y área de origen para el Superusuario (`cuenta_historica`, `evento_origen`, `actividad_bitacora`).
- **Secciones**: **Resumen**, **Cuentas** (activas, inactivas y eliminadas), **Incidencias y Registros**, **Pendientes globales**, **Archivos y Respaldos**, **Actividad cronológica** y **Mi perfil**.
- **Documentación individual**: **Expediente** completo por cuenta y **Ficha documental** por registro, con **impresión/PDF aislada** (solo el expediente seleccionado) y **exportación CSV individual** (`seccion=expediente`).
- **Recuperación y depuración**: restablecimiento de correo/contraseña de cualquier usuario (incluido el Jefe) y módulo de **eliminación permanente selectiva** en PostgreSQL para limpiar datos de prueba.

### Seguridad implementada
- Contraseñas cifradas con **bcrypt** y límite de intentos en login (`RateLimiter` por IP y cuenta+IP, HTTP `429`).
- Tokens **JWT HS256** con huella de versión (`ver`) que invalida sesiones anteriores automáticamente al cambiar contraseña o eliminar cuentas.
- Cabeceras HTTP de seguridad en middleware: `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy` y `Cache-Control: no-store` en endpoints sensibles.

---

## Arquitectura del proyecto (`web/`)

```text
web/
├── alembic/versions/            # Migraciones PostgreSQL (0001 a 0008)
├── app/
│   ├── core/                    # config, db, deps (JWT/RBAC), enums, rate_limit, security
│   ├── models/                  # 11 módulos ORM SQLAlchemy 2.0 (14 tablas)
│   ├── routers/                 # 11 routers FastAPI bajo /api/v1
│   ├── schemas/                 # 12 módulos Pydantic v2 + validadores
│   ├── services/                # 15 servicios de dominio e historial
│   └── main.py                  # App FastAPI, middleware CSP y archivos estáticos
├── static/
│   ├── css/                     # ITCSS modular (base, layout, components, views, responsive)
│   ├── img/                     # logo-zgroup.png
│   └── js/
│       ├── app.js               # Enrutador hash y ciclo de sesión
│       ├── components/ui.js     # Modales, toasts, validadores en vivo
│       ├── services/
│       │   ├── api.js           # Fachada ClienteApi
│       │   └── api/             # models.js, functions.js, routers/{auth,eventos,admin,superadmin}.js
│       └── views/               # hoy, detalle, pendientes, busqueda, tablero, admin, perfil, superadmin/
├── templates/index.html         # Shell SPA único
├── scripts/                     # seed.py, respaldo.sh, restaurar.sh
├── tests/                       # Suite pytest (72 pruebas funcionales y de seguridad)
├── e2e/                         # Pruebas E2E con Playwright + @faker-js/faker
├── Dockerfile
└── docker-compose.yml           # PostgreSQL 16 (5434:5432), API (8001:8000), respaldo diario
```

---

## Puesta en marcha (en `web/`)

### Opción 1: PostgreSQL 16 en Docker + Web/API local (recomendado para desarrollo)

```powershell
cd web
copy .env.example .env           # Configura SECRET_KEY y credenciales seguras
docker compose -p bitacora-web up -d db

python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m scripts.seed jefe@correo.com "Jefe TI" "claveSegura123"

python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Acceso web: http://127.0.0.1:8001/  
Documentación OpenAPI: http://127.0.0.1:8001/api/v1/docs

### Opción 2: Stack completo en Docker (`db` + `api` + respaldos opcionales)

```powershell
cd web
copy .env.example .env           # Cambia SECRET_KEY y contraseñas antes de desplegar
docker compose -p bitacora-web up -d --build
# Con respaldo diario automático:
# docker compose -p bitacora-web --profile respaldo up -d --build
```

Al iniciar, [`docker-entrypoint.sh`](./web/docker-entrypoint.sh) ejecuta automáticamente `alembic upgrade head` y crea los usuarios iniciales definidos en el entorno.

---

## Pruebas automatizadas

### Backend (`pytest`)
```powershell
cd web
python -m pytest -q
```

### End-to-End en navegador real (`Playwright` + `Faker.js`)
```powershell
cd web
npm install
npm run test:e2e                 # Headless con Chrome
npm run test:e2e:headed          # Con navegador visible
```

---

## Resumen de roles

| Capacidad | Asistente | Encargado | Jefe | Superusuario |
| --- | :---: | :---: | :---: | :---: |
| Registrar eventos, notas y compromisos propios | ✔ | ✔ | ✔ | — |
| Cerrar, cancelar, reabrir y corregir registros | | ✔ | ✔ | — |
| Tablero KPI (`K1`–`K12`) y exportar CSV | | ✔ | ✔ | ✔ |
| Administración (Áreas, Subtipos, Usuarios, Roles, Claves API) | | | ✔ | — |
| Mi perfil (cambiar correo y contraseña propios) | ✔ | ✔ | ✔ | ✔ |
| Portal de auditoría, historial de cuentas eliminadas y purga | | | | ✔ |
| Restablecer credenciales de cualquier cuenta | | | | ✔ |

