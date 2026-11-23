# Bitácora TI — Datos: tablas, relaciones y comunicación

Motor: **PostgreSQL 16** · ORM: **SQLAlchemy** · Acceso: solo vía **API FastAPI** (`/api/v1`).  
El escritorio (Tkinter) **no** toca la base; usa HTTP (`desktop/api_client.py`).

---

## 1. Mapa de tablas

| Tabla | Rol |
| --- | --- |
| `usuario` | Personas del sistema (login, autor, responsable) |
| `rol_personalizado` | Roles creados por el jefe con permisos JSON |
| `area` | Áreas de origen (Contabilidad, etc.) |
| `folio_secuencia` | Contador anual para folios `BIT-AAAA-NNNNN` |
| `evento` | Hecho registrado (núcleo del dominio) |
| `seguimiento` | Notas inmutables del evento |
| `compromiso` | Compromisos con fecha límite |
| `auditoria` | Historial de correcciones de cabecera |
| `subtipo` | Ajustes al catálogo (agregados / desactivados) |
| `clave_api` | Claves de solo lectura (hash SHA-256) |
| `uso_clave_api` | Log de accesos con clave API |

Enums en PostgreSQL: `rol`, `tipo_evento`, `estado_evento`, `prioridad_evento`, `estado_compromiso`.

---

## 2. Diagrama de relaciones

```
                    ┌─────────────────────┐
                    │  rol_personalizado  │
                    │  id (PK)            │
                    │  nombre, permisos[] │
                    │  creado_por_id ─────┼──┐
                    └──────────▲──────────┘  │
                               │             │
                     rol_custom_id           │
                               │             │
┌──────────────┐      ┌────────┴────────┐   │
│    area      │      │    usuario      │◄──┘
│ id (PK)      │      │ id (PK)         │
│ nombre       │      │ correo, rol     │
│ activa       │      │ clave_hash      │
└──────▲───────┘      │ activo          │
       │              └────────┬────────┘
       │ area_id               │ autor_id / responsable_id / usuario_id / creada_por_id
       │                       │
┌──────┴───────────────────────┴──────────────────────────────────────┐
│                              evento                                  │
│  id (PK) · folio (UQ) · tipo · subtipo · titulo · descripcion       │
│  fecha_hecho · estado · prioridad · requiere_seguimiento · busqueda │
│  cerrado_en · creado_en                                              │
└──────┬──────────────────┬──────────────────┬────────────────────────┘
       │                  │                  │
       │ 1:N              │ 1:N              │ 1:N
       ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ seguimiento  │  │  compromiso  │  │  auditoria   │
│ evento_id    │  │ evento_id    │  │ evento_id    │
│ autor_id ────┼─►│ responsable_id│ │ usuario_id ──┼─► usuario
│ nota (inm.)  │  │ fecha_limite │  │ campo,       │
│ estado_*     │  │ estado       │  │ valor_ant/nuevo│
└──────────────┘  └──────────────┘  └──────────────┘

┌──────────────┐       ┌──────────────┐
│  clave_api   │──1:N─►│ uso_clave_api│
│ hash (UQ)    │       │ metodo, ruta │
│ creada_por_id│──►usuario            │
└──────────────┘       └──────────────┘

┌──────────────┐   ┌─────────────────┐
│   subtipo    │   │ folio_secuencia │
│ tipo+nombre  │   │ anio (PK)       │
│ (PK comp.)   │   │ ultimo          │
│ activo       │   └─────────────────┘
└──────────────┘
```

### Cardinalidades

| Desde | Hacia | Relación | FK |
| --- | --- | --- | --- |
| `usuario` | `rol_personalizado` | N:1 opcional | `usuario.rol_custom_id` |
| `rol_personalizado` | `usuario` | N:1 | `creado_por_id` |
| `evento` | `area` | N:1 opcional | `area_id` |
| `evento` | `usuario` (autor) | N:1 | `autor_id` |
| `evento` | `usuario` (responsable) | N:1 opcional | `responsable_id` |
| `seguimiento` | `evento` | N:1 | `evento_id` |
| `seguimiento` | `usuario` | N:1 | `autor_id` |
| `compromiso` | `evento` | N:1 | `evento_id` |
| `compromiso` | `usuario` | N:1 | `responsable_id` |
| `auditoria` | `evento` | N:1 | `evento_id` |
| `auditoria` | `usuario` | N:1 | `usuario_id` |
| `clave_api` | `usuario` | N:1 | `creada_por_id` |
| `uso_clave_api` | `clave_api` | N:1 | `clave_id` |

---

## 3. Detalle de columnas

### `usuario`
| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | UUID PK | |
| `nombre` | varchar(120) | |
| `correo` | varchar(255) UQ | login (minúsculas) |
| `rol` | enum `rol` | `jefe` \| `encargado` \| `asistente` |
| `clave_hash` | varchar(255) | bcrypt |
| `activo` | bool | inactivo no entra ni es responsable |
| `rol_custom_id` | UUID FK? | si activo, sus permisos sustituyen al rol base |
| `creado_en` | timestamptz | UTC |

### `rol_personalizado`
| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | UUID PK | |
| `nombre` | varchar(80) UQ | |
| `descripcion` | text | |
| `permisos` | JSON array | valores de `Permiso` |
| `activo` | bool | |
| `creado_por_id` | UUID FK → usuario | |
| `creado_en` | timestamptz | |

### `area`
| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | UUID PK | |
| `nombre` | varchar(120) UQ | |
| `activa` | bool | desactivar no borra eventos viejos |

### `folio_secuencia`
| Columna | Tipo | Notas |
| --- | --- | --- |
| `anio` | int PK | año del folio |
| `ultimo` | int | último número usado |

### `evento` (núcleo)
| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | UUID PK | |
| `folio` | varchar(20) UQ | `BIT-2026-00041` |
| `tipo` | enum | solicitud, incidencia, tarea, visita, otro |
| `subtipo` | varchar(40)? | validado contra catálogo vigente |
| `titulo` | varchar(200) | |
| `descripcion` | text | |
| `referencia` | varchar(500)? | |
| `fecha_hecho` | date | no futura; índice con tipo |
| `area_id` | UUID FK? | |
| `solicitante_nombre` | varchar(120)? | texto libre |
| `requiere_seguimiento` | bool | |
| `estado` | enum | informativo → … → cerrado/cancelado |
| `prioridad` | enum? | baja/media/alta (con seguimiento) |
| `autor_id` | UUID FK | quien registró |
| `responsable_id` | UUID FK? | |
| `creado_en` / `cerrado_en` | timestamptz | |
| `busqueda` | text | texto normalizado (pg_trgm en PG) |

Índices: `fecha_hecho+tipo`, `estado`, `responsable_id`.

### `seguimiento`
Notas **inmutables** (listener SQLAlchemy + trigger Alembic impiden UPDATE/DELETE).

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | UUID PK | |
| `evento_id` | UUID FK | |
| `autor_id` | UUID FK | |
| `nota` | text | |
| `estado_anterior` / `estado_nuevo` | enum? | si la nota es de cambio de estado |
| `creado_en` | timestamptz | |

### `compromiso`
| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | UUID PK | |
| `evento_id` | UUID FK | |
| `descripcion` | text | |
| `responsable_id` | UUID FK | |
| `fecha_limite` | date | |
| `estado` | enum | pendiente → cumplido \| cancelado |
| `cumplido_en` | timestamptz? | |
| `creado_en` | timestamptz | |

### `auditoria`
Una fila por campo corregido en la cabecera del evento.

### `subtipo`
PK compuesta `(tipo, nombre)`. Solo guarda desviaciones del catálogo base en `app.core.enums.SUBTIPOS`.

### `clave_api` / `uso_clave_api`
La clave en claro (`bti_…`) se muestra **una vez**; en BD solo `prefijo` + `hash`. Cada GET con `X-API-Key` inserta en `uso_clave_api` (método + ruta, sin body ni query).

---

## 4. Valores de dominio (enums)

```
Rol:        jefe | encargado | asistente
Tipo:       solicitud | incidencia | tarea | visita | otro
Estado:     informativo → abierto → en_proceso ↔ en_espera → resuelto → cerrado
            (también cancelado; reabrir solo desde cerrado)
Prioridad:  baja | media | alta
Compromiso: pendiente | cumplido | cancelado
```

Subtipos de fábrica (resumen):  
solicitud→ desarrollo, informacion, acceso, soporte · incidencia→ falla, bloqueo, degradacion ·  
tarea→ interna, mantenimiento, despliegue · visita→ presencial, remota · otro→ prestamo, entrega, aviso.

---

## 5. Comunicación de datos

### 5.1 Capas

```
┌─────────────────────┐     HTTPS/JSON      ┌─────────────────────┐
│  Escritorio Tkinter │ ──────────────────► │  FastAPI /api/v1    │
│  desktop/app.py     │  Authorization:     │  routers + schemas  │
│  api_client.py      │  Bearer <JWT>       │  (Pydantic I/O)     │
└─────────────────────┘                     └──────────┬──────────┘
                                                       │ SQLAlchemy
                                                       ▼
                                            ┌─────────────────────┐
                                            │   PostgreSQL 16     │
                                            │   tablas de arriba  │
                                            └─────────────────────┘

┌─────────────────────┐     X-API-Key       ┌─────────────────────┐
│ Programa externo    │ ──────────────────► │ Solo lectura:       │
│ (integración)       │                     │ GET /eventos,       │
└─────────────────────┘                     │ /eventos/{folio},   │
                                            │ /eventos/resumen    │
                                            └─────────────────────┘
```

### 5.2 Flujo de autenticación (sesión humana)

1. `POST /auth/login` `{correo, clave}` → verifica `usuario.clave_hash`.
2. API responde `{token, usuario}`; el token JWT lleva `sub = usuario.id`.
3. Cliente guarda `Authorization: Bearer …` en todas las peticiones.
4. `deps.usuario_actual` lee el token, carga el `usuario` activo y aplica rol/permisos.

### 5.3 Flujo de escritura típico (evento)

1. UI arma JSON (`tipo`, `titulo`, `descripcion`, `area_id`, `requiere_seguimiento`, …).
2. `POST /eventos` → valida área/subtipo/fecha → `folio_secuencia` → inserta `evento` → reindexa `busqueda`.
3. Respuesta `EventoOut` (JSON) con autor/área/responsable embebidos (no FKs crudas en la UI).
4. Cambios de estado → `POST /eventos/{folio}/estado` actualiza `evento` e inserta fila en `seguimiento`.
5. Notas → solo `INSERT` en `seguimiento`. Compromisos → `compromiso` (+ nota automática).
6. Corrección de cabecera → `UPDATE evento` + una fila `auditoria` por campo.

### 5.4 Flujo de lectura / búsqueda

1. `GET /eventos?q=&desde=&hasta=&tipo=&estado=…` arma filtros SQL sobre `evento` (y joins lógicos a compromisos vencidos).
2. Texto: columna `evento.busqueda` (normalizada); en PG índice `pg_trgm`.
3. Respuesta paginada: `{data: [...], meta: {page, page_size, total}}`; con `q` cada ítem puede traer `fragmento`.
4. Detalle: `GET /eventos/{folio}?incluir=seguimientos,compromisos,auditoria` hidrata las 1:N.

### 5.5 KPI

`GET /kpi` no tiene tabla propia: agrega en vivo sobre `evento` y `compromiso` (K1–K12). Algunos son “stock actual” (K3, K4, K8, K9, K11) e ignoran el rango de fechas.

### 5.6 Formato de intercambio

| Capa | Formato |
| --- | --- |
| Red | JSON (UTF-8); CSV solo en `GET /eventos/exportar` |
| Fechas | `date` → `YYYY-MM-DD`; datetimes → ISO-8601 UTC |
| IDs | UUID string |
| Enums | valor string (`en_proceso`, no el nombre Python) |
| Errores de dominio | HTTP `409` + `{"codigo","detalle"}` |
| Validación | HTTP `422` (Pydantic) |

### 5.7 Qué no viaja al cliente

- `clave_hash`, hash de claves API, cuerpo de requests con `X-API-Key`.
- La columna interna `busqueda` (solo se usa en SQL).
- Triggers/listeners de inmutabilidad de notas (regla de servidor).

---

## 6. Migraciones (evolución del esquema)

| Revisión | Aporta |
| --- | --- |
| `0001` | usuario, area, folio_secuencia, evento |
| `0002` | seguimiento, compromiso + inmutabilidad notas |
| `0003` | `evento.busqueda`, auditoria, pg_trgm |
| `0004` | clave_api, uso_clave_api, subtipo |
| `0005` | rol_personalizado + `usuario.rol_custom_id` |

---

## 7. Resumen

- El **evento** es el centro; notas, compromisos y auditoría cuelgan 1:N.
- **Usuarios** participan como autor, responsable o emisor de claves/roles.
- La **comunicación** es siempre API REST → ORM → PostgreSQL; el escritorio y los sistemas externos son clientes HTTP con JWT o `X-API-Key`.
