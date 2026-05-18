#!/bin/bash

# Ruta al archivo de backup
# BACKUP_FILE="./backups/backup_2025-08-04_22-43-20.dump"

# Nombre del contenedor
CONTAINER_NAME="${POSTGRES_CONTAINER_NAME:-nuestra-memoria-postgres}"

# Copiar el archivo de backup al contenedor
echo "📦 Copiando backup al contenedor..."
docker cp "$BACKUP_FILE" "$CONTAINER_NAME":/tmp/restore.dump

# Ejecutar el restore dentro del contenedor
echo "♻️  Restaurando base de datos desde el dump..."
docker exec "$CONTAINER_NAME" sh -lc '
export PGPASSWORD="$POSTGRES_PASSWORD"
pg_restore -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --verbose /tmp/restore.dump
'

# Borrar el archivo dentro del contenedor (opcional)
echo "🧹 Limpiando archivo temporal..."
docker exec "$CONTAINER_NAME" rm /tmp/restore.dump

echo "✅ Restauración completada."
