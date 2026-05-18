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

PROJECT_ID_ARG="${1:-$PROJECT_ID}"

echo "== Importación manual de transcripciones =="
echo "Proyecto: $PROJECT_ID_ARG"
echo "TRANSCRIPTION_PROJECTS_PATH=$TRANSCRIPTION_PROJECTS_PATH"
echo "TRANSCRIPT_SOURCE_PATH=$TRANSCRIPT_SOURCE_PATH"
echo "AUDIO_FILES_PATH=$AUDIO_FILES_PATH"

"${COMPOSE_CMD[@]}" up -d postgres redis web_app
"${COMPOSE_CMD[@]}" exec web_app python scripts/import_segments.py "$PROJECT_ID_ARG"