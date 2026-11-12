#!/bin/sh
set -e
export PYTHONPATH="${PYTHONPATH:-.}"
# Aplica las migraciones antes de arrancar la API.
alembic upgrade head
# Datos iniciales (jefe y áreas) solo si se definen en el entorno. Es idempotente.
if [ -n "$SEED_JEFE_CORREO" ] && [ -n "$SEED_JEFE_CLAVE" ]; then
  python -m scripts.seed "$SEED_JEFE_CORREO" "${SEED_JEFE_NOMBRE:-Jefe TI}" "$SEED_JEFE_CLAVE"
fi
exec "$@"
