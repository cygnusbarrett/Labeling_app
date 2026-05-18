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

usage() {
    cat <<EOF
Uso: $(basename "$0") <comando> [args...]

Comandos:
  up            Levanta el stack en background y reconstruye imagenes
  down          Baja el stack
  restart       Reinicia el stack reconstruyendo imagenes
  ps            Muestra estado de servicios
  logs [svc]    Muestra logs del stack o de un servicio
  config        Muestra el compose renderizado
  shell         Abre shell dentro de web_app
  summary       Imprime la configuracion efectiva cargada desde runtime_config.sh

Edita scripts/runtime_config.sh si cambian rutas del host o mounts.
EOF
}

command_name="${1:-}"
if [[ -z "$command_name" ]]; then
    usage
    exit 1
fi
shift || true

case "$command_name" in
    up)
        "${COMPOSE_CMD[@]}" up -d --build "$@"
        ;;
    down)
        "${COMPOSE_CMD[@]}" down "$@"
        ;;
    restart)
        "${COMPOSE_CMD[@]}" down
        "${COMPOSE_CMD[@]}" up -d --build "$@"
        ;;
    ps)
        "${COMPOSE_CMD[@]}" ps "$@"
        ;;
    logs)
        "${COMPOSE_CMD[@]}" logs -f "$@"
        ;;
    config)
        "${COMPOSE_CMD[@]}" config "$@"
        ;;
    shell)
        "${COMPOSE_CMD[@]}" exec web_app sh
        ;;
    summary)
        runtime_config_summary
        ;;
    *)
        usage
        exit 1
        ;;
esac