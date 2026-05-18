#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/runtime_config.sh"

if command -v docker >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
else
    echo "ERROR: no se encontro docker ni docker-compose en este host" >&2
    exit 1
fi

print_step() {
    echo
    echo "== $1 =="
}

require_file() {
    local path="$1"
    if [[ ! -f "$path" ]]; then
        echo "ERROR: falta archivo requerido: $path" >&2
        exit 1
    fi
}

mask_env_value() {
    sed 's/=.*/=***set***/'
}

normalize_transcription_permissions() {
    local container_root="/app/data/transcription_projects"
    local project_dir="$container_root/$PROJECT_ID"

    "${COMPOSE_CMD[@]}" exec -u root web_app sh -lc '
mkdir -p "$1" &&
chown -R appuser:appuser "$1" &&
chmod a+rwx "$2" "$1" &&
find "$2" -type f \( -name "reconstructed_transcript.json" -o -name "reconstructed_transcript.txt" \) -exec chown appuser:appuser {} + -exec chmod a+rw {} +
' sh "$project_dir" "$container_root"
}

print_step "Verificando checkout y entorno"
require_file "$COMPOSE_FILE"
require_file "$ENV_FILE"

cd "$PROJECT_DIR"

echo "Proyecto: $PROJECT_DIR"
echo "Branch objetivo: $GIT_BRANCH"
echo "Proyecto de smoke test: $PROJECT_ID"
echo "Configuracion cargada desde: $SCRIPT_DIR/runtime_config.sh"

print_step "Actualizando checkout"
git fetch origin
git checkout "$GIT_BRANCH"
git pull --ff-only origin "$GIT_BRANCH"

print_step "Verificando variables criticas"
grep -E '^(POSTGRES_ADMIN_USER|POSTGRES_ADMIN_PASSWORD|APP_DB_USER|APP_DB_PASSWORD|DB_NAME|REDIS_PASSWORD|JWT_SECRET_KEY|SECRET_KEY|DATABASE_URL)=' "$ENV_FILE" | mask_env_value || true

for required_key in POSTGRES_ADMIN_USER POSTGRES_ADMIN_PASSWORD APP_DB_USER APP_DB_PASSWORD DB_NAME REDIS_PASSWORD JWT_SECRET_KEY SECRET_KEY; do
    if ! grep -q "^${required_key}=" "$ENV_FILE"; then
        echo "ERROR: falta ${required_key} en $ENV_FILE" >&2
        exit 1
    fi
done

print_step "Reconstruyendo stack Docker de produccion"
"${COMPOSE_CMD[@]}" down
"${COMPOSE_CMD[@]}" up -d --build

print_step "Estado y logs iniciales"
"${COMPOSE_CMD[@]}" ps
"${COMPOSE_CMD[@]}" logs --tail=200 web_app

print_step "Health checks HTTP"
curl -i --max-time 20 http://127.0.0.1:3000/health
curl -I --max-time 20 http://127.0.0.1:3000/login

print_step "DATABASE_URL efectivo dentro del contenedor"
"${COMPOSE_CMD[@]}" exec web_app sh -lc 'echo "$DATABASE_URL"'

print_step "Confirmando decision_type en PostgreSQL"
"${COMPOSE_CMD[@]}" exec postgres sh -lc 'export PGPASSWORD="$POSTGRES_PASSWORD"; psql -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\d+ segments"' | grep decision_type

print_step "Confirmando codigo esperado dentro de la imagen"
"${COMPOSE_CMD[@]}" exec web_app sh -lc '
grep -n "decision_type" /app/src/routes/transcription_api_routes.py &&
grep -n "submitWord" /app/src/static/js/controllers/transcriptionController.js &&
grep -n "Confirmar con duda" /app/src/templates/transcription_validator.html &&
grep -n "reconstructed_transcript" /app/src/services/reconstructed_transcript_service.py
'

print_step "Normalizando permisos de transcription_projects"
normalize_transcription_permissions

print_step "Regenerando exports del proyecto"
"${COMPOSE_CMD[@]}" exec web_app python scripts/rebuild_transcription_exports.py --project-id "$PROJECT_ID"

print_step "Listando exports reconstruidos"
"${COMPOSE_CMD[@]}" exec web_app sh -lc 'find /app/data/transcription_projects -maxdepth 2 \( -name reconstructed_transcript.json -o -name reconstructed_transcript.txt \) | sort'

cat <<EOF

Smoke test base completado.

Siguiente paso manual recomendado:
1. Abrir /login por el proxy o por un tunel SSH.
2. Probar Confirmar, Confirmar con duda y Descartar.
3. Revisar luego las ultimas filas de segments y los exports reconstruidos.

Consultas utiles:
    ${COMPOSE_CMD[*]} exec postgres sh -lc 'export PGPASSWORD="\$POSTGRES_PASSWORD"; psql -h 127.0.0.1 -U "\$POSTGRES_USER" -d "\$POSTGRES_DB" -c "SELECT id, project_id, review_status, decision_type, text_revised FROM segments ORDER BY updated_at DESC LIMIT 10;"'
  ${COMPOSE_CMD[*]} exec web_app sh -lc 'ls -lh /app/data/transcription_projects/${PROJECT_ID}/reconstructed_transcript.*'

EOF