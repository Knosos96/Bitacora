# Bitácora TI — Funciones de API y funcionamiento

Base URL: `http://localhost:8000/api/v1`  
Docs interactivas: `http://localhost:8000/api/v1/docs`  
OpenAPI: `http://localhost:8000/api/v1/openapi.json`

Autenticación de sesión: encabezado `Authorization: Bearer <token>` (JWT tras login).  
API externa (solo lectura): encabezado `X-API-Key: bti_...` (solo en GET de eventos/resumen).

---

## Salud

| Método | Ruta | Función | Quién |
| --- | --- | --- | --- |
| `GET` | `/salud` | Comprueba que la API responde `{"ok": true}` | Público |

---

## Auth (`/auth`)

| Método | Ruta | Función | Quién |
| --- | --- | --- | --- |
| `POST` | `/auth/login` | Valida correo/clave; devuelve JWT + datos del usuario | Público |
| `GET` | `/auth/yo` | Devuelve el usuario autenticado | Cualquier usuario activo |

**Funcionamiento:** si el correo no existe, el usuario está inactivo o la clave no coincide → `401`. El token dura `TOKEN_HORAS` (por defecto 12 h).

---

## Usuarios (`/usuarios`)

| Método | Ruta | Función | Quién |
| --- | --- | --- | --- |
| `POST` | `/usuarios` | Crea usuario (nombre, correo, rol, clave) | Jefe |
| `GET` | `/usuarios` | Lista usuarios ordenados por nombre | Jefe, encargado |
| `PATCH` | `/usuarios/{id}` | Cambia nombre, rol, activo o restablece clave | Jefe |

**Funcionamiento:** no se borran usuarios; se desactivan. Correo duplicado → `400`. Debe quedar al menos un jefe activo (`409 ultimo_jefe`). El jefe no puede desactivarse a sí mismo (`409 sin_permiso`).

---

## Áreas (`/areas`)

| Método | Ruta | Función | Quién |
| --- | --- | --- | --- |
| `GET` | `/areas` | Lista áreas activas; `?incluir_inactivas=true` incluye inactivas | Todos (inactivas: encargado/jefe) |
| `POST` | `/areas` | Crea área por nombre | Encargado, jefe |
| `PATCH` | `/areas/{id}` | Renombra o activa/desactiva | Encargado, jefe |

**Funcionamiento:** desactivar no altera eventos ya registrados. Nombre duplicado → `400`.

---

## Eventos (`/eventos`)

| Método | Ruta | Función | Quién |
| --- | --- | --- | --- |
| `POST` | `/eventos` | Registra evento; genera folio `BIT-AAAA-NNNNN` | Todos |
| `GET` | `/eventos` | Lista/busca con filtros y paginación | JWT o clave API |
| `GET` | `/eventos/resumen` | Conteos por tipo en un rango | JWT o clave API |
| `GET` | `/eventos/exportar` | Exporta CSV (máx. 20 000 filas, UTF-8 BOM) | Encargado, jefe |
| `GET` | `/eventos/{folio}` | Detalle; `?incluir=seguimientos,compromisos,auditoria` | JWT o clave API (sin auditoría) |
| `PATCH` | `/eventos/{folio}` | Seguimiento/responsable/prioridad o corrección de cabecera | Según campo |
| `POST` | `/eventos/{folio}/estado` | Cambia estado (incl. cerrar/cancelar/reabrir) | Según transición |
| `GET/POST` | `/eventos/{folio}/seguimientos` | Lista / agrega notas inmutables | Todos |
| `GET/POST` | `/eventos/{folio}/compromisos` | Lista / crea compromisos | Todos |

### Alta (`POST /eventos`)
- Tipos: `solicitud`, `incidencia`, `visita`, `prestamo`, `tarea_interna`.
- Sin seguimiento → estado `informativo`. Con seguimiento → `abierto`, responsable (autor por defecto) y prioridad media.
- `fecha_hecho` no puede ser futura. Subtipo debe estar vigente para el tipo.

### Búsqueda (`GET /eventos`)
- Sin filtros ni fechas → pantalla **Hoy**.
- Con `q`, estado, área, responsable, seguimiento o vencidos y sin fechas → histórico completo.
- `q` busca texto normalizado (sin acentos, todas las palabras); si es folio, abre ese evento.
- Con clave API: `desde` y `hasta` **obligatorios**; no admite `responsable_id`, `seguimiento` ni `vencidos`.

### Estados
- `informativo` → solo sale activando seguimiento (`abierto`).
- `abierto` → `en_proceso` \| `en_espera` \| `resuelto` \| `cancelado`.
- `en_proceso` ↔ `en_espera`; `resuelto` → `en_proceso` \| `cerrado`.
- Reabrir: `POST .../estado` con `estado=abierto` y nota obligatoria sobre evento **cerrado** (encargado/jefe). Cancelado no se reabre.
- Cerrar/cancelar con compromisos pendientes → `409 compromisos_pendientes` salvo `resolver_compromisos: cumplir|cancelar`.
- Errores de dominio: `409` con `codigo`/`detalle` (`sin_permiso`, `transicion_invalida`, `sin_seguimiento`, `evento_cerrado`, …).

### Corrección de cabecera (`PATCH`)
- Campos: título, descripción, referencia, solicitante, fecha_hecho, área, tipo, subtipo.
- Autor el mismo día; después solo encargado/jefe. Cada cambio queda en auditoría.

---

## Compromisos (`/compromisos`)

| Método | Ruta | Función | Quién |
| --- | --- | --- | --- |
| `PATCH` | `/compromisos/{id}` | Marca cumplido o cancelado (no se borra) | Responsable, encargado, jefe |

**Funcionamiento:** solo desde `pendiente`. Evento cerrado/cancelado → `409 evento_cerrado`. Escribe nota automática en el seguimiento.

---

## Pendientes (`/pendientes`)

| Método | Ruta | Función | Quién |
| --- | --- | --- | --- |
| `GET` | `/pendientes` | Eventos abiertos + compromisos pendientes | Todos |

**Query:** `solo_mios`, `solo_vencidos`. El asistente siempre ve solo lo suyo; encargado/jefe ven todo (o los suyos con `solo_mios`).

---

## KPI / Tablero (`/kpi`)

| Método | Ruta | Función | Quién |
| --- | --- | --- | --- |
| `GET` | `/kpi` | Tablero K1–K12; sin fechas = semana en curso | Encargado, jefe |
| `GET` | `/kpi/{K1..K12}` | Lista de eventos/compromisos que explican el número | Encargado, jefe |

| KPI | Significado |
| --- | --- |
| K1 | Volumen por tipo |
| K2 | Con seguimiento vs informativos |
| K3 | Stock abierto (ahora) |
| K4 | Resueltos sin cerrar (ahora) |
| K5 | Tiempo medio de atención |
| K6 | Cerrados en el rango |
| K7 | Cumplimiento de compromisos |
| K8 | Compromisos vencidos ahora |
| K9 | Carga máxima por responsable |
| K10 | Top 5 áreas de origen |
| K11 | Antigüedad máxima de abierto |
| K12 | Incidencias en el rango |

K3, K4, K8, K9 y K11 no dependen del rango. Asistente → `403`.

---

## Claves API (`/claves-api`) — Sprint 5

| Método | Ruta | Función | Quién |
| --- | --- | --- | --- |
| `POST` | `/claves-api` | Emite clave; el valor en claro se muestra **una sola vez** | Jefe |
| `GET` | `/claves-api` | Lista (nombre, prefijo, usos, revocación) | Jefe |
| `DELETE` | `/claves-api/{id}` | Revoca (conserva historial de uso) | Jefe |

**Endpoints permitidos con `X-API-Key`:** solo `GET /eventos`, `GET /eventos/{folio}`, `GET /eventos/resumen`. Cualquier otro → `401`. Cada uso registra fecha, método y ruta (no el cuerpo).

---

## Subtipos (`/subtipos`)

| Método | Ruta | Función | Quién |
| --- | --- | --- | --- |
| `GET` | `/subtipos` | Catálogo; filtro opcional por `tipo` | Todos |
| `POST` | `/subtipos` | Agrega o reactiva subtipo | Encargado, jefe |
| `PATCH` | `/subtipos/{tipo}/{nombre}` | Activa o desactiva | Encargado, jefe |

**Funcionamiento:** desactivar no cambia eventos existentes; solo deja de ofrecarse en altas nuevas.

---

## Roles personalizados (`/roles`)

| Método | Ruta | Función | Quién |
| --- | --- | --- | --- |
| `GET` | `/roles` | Lista roles personalizados | Jefe, encargado |
| `GET` | `/roles/permisos` | Catálogo de permisos disponibles | Jefe |
| `POST` | `/roles` | Crea rol con lista de permisos | Jefe |
| `PATCH` | `/roles/{id}` | Edita nombre, descripción, permisos o activo | Jefe |
| `DELETE` | `/roles/{id}` | Desactiva y quita asignación a usuarios | Jefe |
| `POST` | `/roles/asignar` | Asigna o quita rol a un usuario (`rol_id=null` lo quita) | Jefe |

---

## Matriz rápida de permisos (roles base)

| Acción | Asistente | Encargado | Jefe |
| --- | :-: | :-: | :-: |
| Login, registrar, buscar, notas, compromisos, pendientes propios | ✔ | ✔ | ✔ |
| Avanzar sus eventos hasta `resuelto` | ✔ | ✔ | ✔ |
| Cerrar, cancelar, reabrir, asignar responsable | | ✔ | ✔ |
| Corregir cabecera ajena / días anteriores | | ✔ | ✔ |
| Tablero KPI y exportar CSV | | ✔ | ✔ |
| Áreas y subtipos | | ✔ | ✔ |
| Usuarios, claves API y roles | | | ✔ |

---

## Cómo probar tras virtualizar

```bash
# Salud
curl -s http://localhost:8000/api/v1/salud

# Login (credenciales de SEED_JEFE_* en .env)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"correo":"jefe@correo.com","clave":"claveSegura123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')

curl -s http://localhost:8000/api/v1/auth/yo -H "Authorization: Bearer $TOKEN"
```

Suite automatizada (sin Docker): `pytest -q`
