# Bitácora TI — Descripción del Proyecto

## ¿Qué es Bitácora TI?

**Bitácora TI** es un sistema de registro y seguimiento de eventos del departamento de Tecnología de la Información (TI). Permite anotar, rastrear y gestionar todo lo que ocurre en el área: solicitudes, incidencias, visitas, préstamos, tareas internas y más.

> El objetivo es que el equipo de TI tenga una memoria institucional confiable y pueda responder preguntas como "¿qué nos pidió Contabilidad esta semana?" o "¿qué compromisos están pendientes?" sin recurrir a chats, correos ni papel.

---

## Arquitectura

```
bitacora-ti/
├── app/              # Backend: API REST con FastAPI + PostgreSQL
│   ├── main.py       # Punto de entrada de la API
│   ├── models.py     # Modelos SQLAlchemy (Usuario, Evento, Seguimiento, etc.)
│   ├── schemas.py    # Esquemas Pydantic (validación de entrada/salida)
│   ├── routers/      # Endpoints organizados por dominio
│   │   ├── auth.py        # Autenticación JWT
│   │   ├── eventos.py     # CRUD de eventos, búsqueda, exportación CSV
│   │   ├── usuarios.py    # Gestión de usuarios
│   │   ├── areas.py       # Áreas del departamento
│   │   ├── compromisos.py # Compromisos por evento
│   │   ├── pendientes.py  # Vista de pendientes y vencidos
│   │   ├── kpi.py         # Indicadores de gestión K1–K12
│   │   ├── claves.py      # Claves API de solo lectura
│   │   └── subtipos.py    # Administración de subtipos de eventos
│   ├── config.py     # Configuración por variables de entorno
│   ├── db.py         # Conexión SQLAlchemy
│   ├── deps.py       # Dependencias (autenticación, control de roles)
│   ├── security.py   # Hashing bcrypt + tokens JWT
│   ├── estados.py    # Máquina de estados de eventos
│   ├── busqueda.py   # Motor de búsqueda full-text normalizado
│   ├── folio.py      # Generador de folios únicos (BIT-AAAA-NNNNN)
│   ├── kpi.py        # Cálculo de indicadores K1–K12
│   └── subtipos.py   # Catálogo de subtipos
├── alembic/          # Migraciones de base de datos
├── desktop/          # Aplicación de escritorio (Tkinter)
│   ├── app.py        # Interfaz gráfica completa
│   └── api_client.py # Cliente HTTP para la API
├── scripts/          # Utilidades de administración
│   ├── seed.py       # Creación del primer jefe y áreas
│   ├── respaldo.sh   # Respaldo manual de la base de datos
│   └── restaurar.sh  # Restauración de respaldo
├── tests/            # Suite de pruebas automatizadas (pytest + SQLite en memoria)
├── Dockerfile        # Imagen Docker de la API
├── docker-compose.yml# Orquestación: db (PostgreSQL 16) + api (FastAPI)
└── PILOTO.md         # Guía de semana piloto
```

---

## Funcionalidades por Sprint

### Sprint 1 — Base del sistema
- Autenticación con JWT (login, roles: `jefe`, `encargado`, `asistente`)
- Gestión de **usuarios** y **áreas**
- Registro de **eventos** con folio único automático (`BIT-AAAA-NNNNN`)
- Tipos de evento: `solicitud`, `incidencia`, `visita`, `prestamo`, `tarea_interna`

### Sprint 2 — Seguimiento y compromisos
- Activar/desactivar seguimiento en eventos
- **Notas de seguimiento** (inmutables: no se editan ni borran)
- **Compromisos** con fecha límite y estado (pendiente / cumplido / cancelado)
- **Máquina de estados**: `informativo → abierto → en_proceso ↔ en_espera → resuelto → cerrado`
- **Pendientes**: vista de eventos abiertos y compromisos vencidos

### Sprint 3 — Búsqueda e historial
- Búsqueda full-text normalizada (sin acentos, plurales, cualquier orden de palabras)
- Filtros avanzados: fecha, tipo, estado, área, responsable, seguimiento, vencidos
- **Historial de auditoría**: qué campo cambió, quién lo cambió y cuándo
- Corrección de cabecera de eventos con trazabilidad completa

### Sprint 4 — Tablero del jefe (KPI)
- **12 indicadores de gestión** (K1–K12) calculados sobre cualquier rango de fechas
- K1: Volumen por tipo | K2: Con/sin seguimiento | K3: Abiertos | K4: Cerrados a tiempo
- K5: Por tipo cerrado | K7: Compromisos a tiempo vs fuera | K9: Carga por responsable | K10: Por área
- Desglose de cada KPI con la lista de eventos que lo componen

### Sprint 5 — API de solo lectura (integración externa)
- Claves API con hash SHA-256 (se ven una sola vez al crearlas)
- Endpoints de solo lectura para programas externos con registro de cada acceso
- El jefe emite y revoca claves desde la interfaz de administración

### Sprint 6 — Administración, respaldos y piloto
- **Reabrir** eventos cerrados o cancelados (con nota obligatoria, solo jefe/encargado)
- **Exportar CSV** de resultados de búsqueda
- Gestión completa de **usuarios** (crear, activar/desactivar, cambiar rol)
- Administración de **subtipos** de eventos (agregar, activar/desactivar)
- **Respaldo automático diario** (perfil Docker `respaldo`)
- Scripts de respaldo manual y ensayo de restauración
- Guía completa de semana piloto (`PILOTO.md`)

---

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 + FastAPI 0.115 |
| Base de datos | PostgreSQL 16 |
| ORM / Migraciones | SQLAlchemy 2.0 + Alembic |
| Autenticación | JWT (PyJWT) + bcrypt |
| Interfaz de escritorio | Tkinter (incluida en Python) |
| Contenedores | Docker + Docker Compose |
| Pruebas | pytest + httpx (SQLite en memoria) |

---

## Inicio rápido

### Con Docker (recomendado)
```bash
cp .env.example .env        # Ajusta SECRET_KEY y credenciales
docker compose up -d --build
# API disponible en: http://localhost:8000/api/v1/docs
```

### Aplicación de escritorio
Con la API corriendo:
```bash
python -m desktop.app
```

### Credenciales iniciales (configurables en `.env`)
- **Correo:** `jefe@correo.com`
- **Clave:** `claveSegura123`

---

## Pruebas
```bash
pytest -q   # No requiere PostgreSQL ni Docker (usa SQLite en memoria)
```

---

## Roles de usuario

| Rol | Permisos |
|---|---|
| `jefe` | Acceso total: tablero KPI, administración, claves API, reabrir/cancelar/cerrar |
| `encargado` | Gestión de eventos, compromisos, estados, correcciones |
| `asistente` | Registrar eventos, notas y compromisos propios, avanzar estados hasta `resuelto` |

