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
