#!/bin/sh
# Ensayo de restauración: respalda, restaura en una base temporal y compara los conteos.
# Es la prueba de que el respaldo sirve de verdad. Hay que correrlo al menos una vez antes de la piloto.
set -eu
cd "$(dirname "$0")/.."
TEMP="bitacora_ensayo"
./scripts/respaldo.sh respaldos
ARCHIVO="$(ls -1t respaldos/bitacora-*.sql.gz | head -n 1)"
./scripts/restaurar.sh "$ARCHIVO" "$TEMP"

contar() {  # $1 = base, $2 = tabla
  docker compose exec -T db sh -c "psql -tA -U \"\$POSTGRES_USER\" -d $1 -c 'SELECT count(*) FROM $2'"
}
FALLO=0
for tabla in usuario area evento seguimiento compromiso auditoria clave_api; do
  ORIGEN="$(contar "${POSTGRES_DB:-bitacora}" "$tabla" | tr -d '[:space:]')"
  COPIA="$(contar "$TEMP" "$tabla" | tr -d '[:space:]')"
  if [ "$ORIGEN" = "$COPIA" ]; then
    echo "OK    $tabla: $ORIGEN filas"
  else
    echo "FALLA $tabla: original=$ORIGEN restaurada=$COPIA"; FALLO=1
  fi
done
docker compose exec -T db sh -c "dropdb -U \"\$POSTGRES_USER\" $TEMP"
[ "$FALLO" -eq 0 ] && echo "Ensayo correcto: el respaldo se restaura completo." || { echo "ENSAYO FALLIDO" >&2; exit 1; }
