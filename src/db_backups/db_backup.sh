#!/bin/bash

set -e

CONTAINER_NAME="${POSTGRES_CONTAINER_NAME:-nuestra-memoria-postgres}"
BACKUP_DIR="${HOST_BACKUPS:-/home/cdgutierrez2/backups}/labeling_app"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
FILENAME="backup_${TIMESTAMP}.dump"

# Crear carpeta si no existe
mkdir -p "$BACKUP_DIR"

# Crear el backup dentro del contenedor
docker exec -t "$CONTAINER_NAME" pg_dump -U "${DB_USER}" -d "${DATABASE_NAME}" -F c -f /tmp/backup.dump

# Copiar el backup al host
docker cp "$CONTAINER_NAME:/tmp/backup.dump" "${BACKUP_DIR}/${FILENAME}"

# Eliminar el backup temporal del contenedor
docker exec "$CONTAINER_NAME" rm /tmp/backup.dump

echo "✅ Backup guardado en: ${BACKUP_DIR}/${FILENAME}"
