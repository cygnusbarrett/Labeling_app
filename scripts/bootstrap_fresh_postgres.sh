#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/runtime_config.sh"

if command -v docker >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
else
    echo "ERROR: no se encontró docker ni docker-compose" >&2
    exit 1
fi

for required_key in POSTGRES_ADMIN_USER POSTGRES_ADMIN_PASSWORD APP_DB_USER APP_DB_PASSWORD DB_NAME REDIS_PASSWORD JWT_SECRET_KEY SECRET_KEY; do
    if ! grep -q "^${required_key}=" "$ENV_FILE"; then
        echo "ERROR: falta ${required_key} en $ENV_FILE" >&2
        exit 1
    fi
done

POSTGRES_DATA_DIR="$HOST_DOCKER_DATA/postgres"

echo "== Bootstrap limpio PostgreSQL =="
echo "Proyecto: $PROJECT_DIR"
echo "Postgres data dir: $POSTGRES_DATA_DIR"
echo "Project import target: ${1:-$PROJECT_ID}"
echo
echo "ADVERTENCIA: esto elimina la base PostgreSQL persistida actual."
read -r -p "Escribe RESET para continuar: " confirmation

if [[ "$confirmation" != "RESET" ]]; then
    echo "Cancelado"
    exit 1
fi

"${COMPOSE_CMD[@]}" down
rm -rf "$POSTGRES_DATA_DIR"
mkdir -p "$POSTGRES_DATA_DIR"

"${COMPOSE_CMD[@]}" up -d postgres redis web_app

echo "Esperando health check de web_app..."
for attempt in {1..20}; do
    if curl -fsS http://127.0.0.1:3000/health >/dev/null 2>&1; then
        break
    fi
    sleep 3
done

curl -fsS http://127.0.0.1:3000/health >/dev/null

"$SCRIPT_DIR/import_runtime_sources.sh" "${1:-$PROJECT_ID}"

echo
echo "Bootstrap completado."
echo "Admin SQL PostgreSQL: definido por POSTGRES_ADMIN_USER en $ENV_FILE"
echo "Password admin SQL: guardado en POSTGRES_ADMIN_PASSWORD dentro de $ENV_FILE"
echo "Admin de plataforma: admin / admin123"
echo "Siguiente paso recomendado: entrar a la app y crear usuarios anotadores desde administración o con src/scripts/create_user.py"