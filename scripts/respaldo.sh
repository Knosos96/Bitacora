#!/bin/sh
# Copia de seguridad de la base. Uso:  ./scripts/respaldo.sh [carpeta_destino]
# Genera respaldos/bitacora-AAAAMMDD-HHMMSS.sql.gz y conserva los últimos 14.
set -eu
DESTINO="${1:-respaldos}"
mkdir -p "$DESTINO"
ARCHIVO="$DESTINO/bitacora-$(date +%Y%m%d-%H%M%S).sql.gz"

docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' | gzip > "$ARCHIVO"

# Un respaldo vacío o truncado no sirve: se descarta y se avisa.
if [ "$(gzip -dc "$ARCHIVO" | wc -c)" -lt 500 ]; then
  rm -f "$ARCHIVO"
  echo "ERROR: el respaldo salió vacío" >&2
  exit 1
fi
echo "Respaldo creado: $ARCHIVO"

# Retención: se conservan los 14 más recientes.
ls -1t "$DESTINO"/bitacora-*.sql.gz 2>/dev/null | tail -n +15 | while read -r viejo; do rm -f "$viejo"; done
