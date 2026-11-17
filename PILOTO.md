# Semana piloto — guía

Objetivo (sección 13 del diseño): una semana completa usando **solo la bitácora**, y el viernes el encargado
responde "¿qué nos pidió Contabilidad?" y "¿qué compromiso sigue abierto?" sin mirar otra cosa.

## Antes de empezar
1. `docker compose up -d --build` y entrar con el jefe.
2. Crear los usuarios reales (jefe → Administración → Usuarios) y las áreas reales.
3. **Ensayo de restauración**: `./scripts/ensayo_restauracion.sh`. Debe terminar en "Ensayo correcto".
4. Activar el respaldo diario: `docker compose --profile respaldo up -d`.
5. El jefe emite la clave del programa externo (Administración → Claves API) y se la entrega por un canal seguro.
   Se ve **una sola vez**.
6. Opcional: correr `pytest tests/test_piloto.py -q`. Es el mismo guion de abajo, automatizado.

## Qué se anota y cómo se comprueba
| Día | Qué se anota | Cómo se comprueba |
| --- | --- | --- |
| Lunes | Solicitud de desarrollo de otra área, con seguimiento y compromiso al viernes | Aparece en K3 y en Pendientes |
| Lunes | Préstamo de una herramienta, sin seguimiento | La búsqueda por el nombre de la herramienta lo encuentra; no está en K3 |
| Martes | Visita de un jefe de área | Búsqueda con tipo=visita y esa fecha, en pantalla y por API |
| Miércoles | Incidencia del ambiente de pruebas, en espera de un proveedor | La nota dice de quién se espera; estado `en_espera` |
| Jueves | Tarea interna de un script, asignada a un asistente | Se ve en su carga (K9) |
| Viernes | Se cumple el compromiso del lunes y el encargado cierra | K7 lo cuenta a tiempo; K5 incluye el cierre |
| Viernes | Consulta del programa externo, lunes a viernes, tipo solicitud | Devuelve la solicitud del lunes y cualquier otra solicitud de la semana |

## Qué observar y anotar (para corregir en la semana)
- Cuánto tarda anotar un hecho. Si pasa de un minuto, el equipo volverá a la memoria.
- Textos pobres ("se pidió info"): revisar los títulos y descripciones reales el jueves.
- Duplicados (dos personas anotan lo mismo): el encargado cancela uno; el folio evita confundirlos.
- Permisos que estorban o que faltan (quién no pudo hacer algo que debía).
- Búsquedas que no encontraron lo esperado: anotar qué palabra se usó y qué texto tenía el evento.

## Cierre de la semana
El encargado, solo con la aplicación:
1. Búsqueda por área = Contabilidad y rango de la semana → qué se pidió.
2. Pendientes → compromisos abiertos y vencidos.
3. Tablero de la semana → K1 a K12.
4. Exportar CSV de la semana (Búsqueda → Exportar CSV) para archivo.
5. Respaldo final: `./scripts/respaldo.sh`.

La piloto se aprueba si el punto 1 y el punto 2 se contestaron sin recurrir a memoria, chat ni papel.
