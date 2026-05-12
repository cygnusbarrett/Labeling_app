#!/bin/bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$PROJECT_DIR/docker-compose.prod.yml}"
COMPOSE=(docker compose -f "$COMPOSE_FILE")
PROJECT_ID=""
SKIP_CLEAN=0
PRINT_PROXY_GUIDE=0

usage() {
    cat <<'EOF'
Uso:
  scripts/reimport_project_safe.sh --project-id <project_id> [--skip-clean] [--print-proxy-guide]

Qué hace:
  1. Verifica que postgres y web_app estén arriba.
  2. Muestra los conteos actuales del proyecto.
  3. Hace un respaldo lógico del proyecto en PostgreSQL.
  4. Limpia filas previas del proyecto salvo que uses --skip-clean.
  5. Reimporta el proyecto con el importador idempotente.
  6. Muestra los conteos finales.

Opciones:
  --project-id <id>      ID del proyecto a reimportar. Ej: memoria_1970_1990
  --skip-clean           Reimporta sin borrar antes. Util cuando ya confías en la idempotencia.
  --print-proxy-guide    Imprime la forma segura de publicar la web via reverse proxy.
  -h, --help             Muestra esta ayuda.

Seguridad de exposicion publica:
  - web_app debe seguir publicado solo en 127.0.0.1:3000.
  - Abre al exterior un reverse proxy del servidor en 80/443.
  - No expongas 3000/tcp directamente a Internet.
EOF
}

print_proxy_guide() {
    cat <<'EOF'

Publicacion segura recomendada:

1. Mantener Flask privado en el host:
   docker-compose.prod.yml ya publica web_app como 127.0.0.1:3000:3000.

2. Publicar solo un reverse proxy del servidor:
   Opcion A, recomendada: Nginx/Caddy del host con TLS hacia http://127.0.0.1:3000
   Opcion B: levantar el perfil edge del compose si quieres usar el Nginx del repo.

3. Ejemplo minimo de Nginx en el host:

   server {
       listen 80;
       server_name TU_DOMINIO;
       return 301 https://$host$request_uri;
   }

   server {
       listen 443 ssl http2;
       server_name TU_DOMINIO;

       ssl_certificate /etc/letsencrypt/live/TU_DOMINIO/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/TU_DOMINIO/privkey.pem;

       location / {
           proxy_pass http://127.0.0.1:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }

4. Si prefieres el proxy del compose del repo:
   docker compose -f docker-compose.prod.yml --profile edge up -d nginx

5. Firewall del servidor:
   - permitir 22/tcp solo para admin
   - permitir 80/tcp y 443/tcp
   - no permitir 3000/tcp, 5432/tcp, 6379/tcp desde Internet

EOF
}

run_psql() {
    local sql="$1"
    "${COMPOSE[@]}" exec -T postgres sh -lc \
        "export PGPASSWORD=\"\$POSTGRES_PASSWORD\"; psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -v ON_ERROR_STOP=1 -P pager=off -c \"$sql\""
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
        --skip-clean)
            SKIP_CLEAN=1
            shift
            ;;
        --print-proxy-guide)
            PRINT_PROXY_GUIDE=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Argumento no reconocido: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ -z "$PROJECT_ID" ]]; then
    echo "Debes indicar --project-id <id>" >&2
    usage >&2
    exit 1
fi

if [[ ! "$PROJECT_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "project_id invalido: usa solo letras, numeros, punto, guion y guion bajo" >&2
    exit 1
fi

if [[ "$PRINT_PROXY_GUIDE" -eq 1 ]]; then
    print_proxy_guide
fi

echo "==> Verificando servicios base"
"${COMPOSE[@]}" up -d postgres redis web_app >/dev/null

echo "==> Conteos actuales"
run_psql "SELECT relname AS table_name, n_live_tup::bigint AS approx_rows FROM pg_stat_user_tables ORDER BY relname;"
run_psql "SELECT id, total_words, words_to_review, words_completed, status FROM transcription_projects WHERE id = '$PROJECT_ID';"

echo "==> Respaldo logico del proyecto $PROJECT_ID"
timestamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="${PROJECT_BACKUP_DIR:-$PROJECT_DIR/data/backups/manual_reimports}"
mkdir -p "$backup_dir"
backup_file="$backup_dir/${PROJECT_ID}-${timestamp}.sql"

"${COMPOSE[@]}" exec -T postgres sh -lc \
    "export PGPASSWORD=\"\$POSTGRES_PASSWORD\"; pg_dump -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" --data-only --inserts --table=transcription_projects --table=segments --table=words | grep -F \"$PROJECT_ID\" || true" \
    > "$backup_file"

echo "Respaldo escrito en: $backup_file"

if [[ "$SKIP_CLEAN" -eq 0 ]]; then
    echo "==> Limpiando filas previas del proyecto"
    run_psql "DELETE FROM words WHERE project_id = '$PROJECT_ID'; DELETE FROM segments WHERE project_id = '$PROJECT_ID'; DELETE FROM transcription_projects WHERE id = '$PROJECT_ID';"
else
    echo "==> Saltando limpieza previa por --skip-clean"
fi

echo "==> Reimportando proyecto"
"${COMPOSE[@]}" exec -T web_app sh -lc "cd /app && python src/scripts/import_segments.py '$PROJECT_ID'"

echo "==> Conteos finales"
run_psql "SELECT relname AS table_name, n_live_tup::bigint AS approx_rows FROM pg_stat_user_tables ORDER BY relname;"
run_psql "SELECT id, total_words, words_to_review, words_completed, status FROM transcription_projects WHERE id = '$PROJECT_ID';"

echo "==> Recomendacion de exposicion publica"
print_proxy_guide