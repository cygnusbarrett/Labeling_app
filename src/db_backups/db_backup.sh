#!/bin/bash

set -e

CONTAINER_NAME="${POSTGRES_CONTAINER_NAME:-nuestra-memoria-postgres}"
BACKUP_DIR="${HOST_BACKUPS:-/home/cdgutierrez2/backups}/labeling_app"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
FILENAME="backup_${TIMESTAMP}.dump"

# Crear carpeta si no existe
mkdir -p "$BACKUP_DIR"

# Crear el backup dentro del contenedor usando el admin SQL del motor
docker exec "$CONTAINER_NAME" sh -lc '
export PGPASSWORD="$POSTGRES_PASSWORD"
pg_dump -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c -f /tmp/backup.dump
'

# Copiar el backup al host
docker cp "$CONTAINER_NAME:/tmp/backup.dump" "${BACKUP_DIR}/${FILENAME}"

# Eliminar el backup temporal del contenedor
docker exec "$CONTAINER_NAME" rm /tmp/backup.dump

echo "✅ Backup guardado en: ${BACKUP_DIR}/${FILENAME}"
