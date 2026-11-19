#!/bin/sh
# Restaura un respaldo en una base NUEVA (no toca la actual). Uso:
#   ./scripts/restaurar.sh respaldos/bitacora-XXXX.sql.gz [nombre_base_destino]
# Por defecto la base destino se llama bitacora_restaurada. Si ya existe, se recrea.
set -eu
ARCHIVO="${1:?Indica el archivo de respaldo}"
DESTINO="${2:-bitacora_restaurada}"

docker compose exec -T db sh -c "dropdb -U \"\$POSTGRES_USER\" --if-exists $DESTINO && createdb -U \"\$POSTGRES_USER\" $DESTINO"
gzip -dc "$ARCHIVO" | docker compose exec -T db sh -c "psql -q -v ON_ERROR_STOP=1 -U \"\$POSTGRES_USER\" -d $DESTINO" > /dev/null
echo "Restaurado en la base '$DESTINO'."
