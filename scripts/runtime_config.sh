#!/bin/bash

# Fuente de verdad para inputs operativos editables por usuario.
# Si cambian directorios del host o mounts del contenedor, actualiza este archivo.

if [[ -n "${LABELING_APP_RUNTIME_CONFIG_LOADED:-}" ]]; then
    return 0 2>/dev/null || exit 0
fi

export LABELING_APP_RUNTIME_CONFIG_LOADED=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"

# Archivos base
export PROJECT_DIR
export COMPOSE_FILE="${COMPOSE_FILE:-$PROJECT_DIR/docker-compose.prod.yml}"
export ENV_FILE="${ENV_FILE:-$PROJECT_DIR/envs/production.env}"

# Parámetros operativos frecuentes
export PROJECT_ID="${PROJECT_ID:-memoria_1970_1990}"
export GIT_BRANCH="${GIT_BRANCH:-feat/jumbita-dev-migration}"

# Directorios del host en jumbita
export HOST_DOCKER_PROJECTS="${HOST_DOCKER_PROJECTS:-/home/cdgutierrez2/docker_projects}"
export HOST_DOCKER_DATA="${HOST_DOCKER_DATA:-/home/cdgutierrez2/docker_data}"
export HOST_BACKUPS="${HOST_BACKUPS:-/home/cdgutierrez2/backups}"
export HOST_TRANSCRIPT_SOURCE="${HOST_TRANSCRIPT_SOURCE:-/home/cdgutierrez2/transcripciones}"
export HOST_AUDIO_SOURCE="${HOST_AUDIO_SOURCE:-/home/cdgutierrez2/solo_es_73-90}"

# Rutas internas del contenedor web_app
export TRANSCRIPTION_PROJECTS_PATH="${TRANSCRIPTION_PROJECTS_PATH:-/app/data/transcription_projects}"
export TRANSCRIPT_SOURCE_PATH="${TRANSCRIPT_SOURCE_PATH:-/app/data/transcriptions}"
export AUDIO_FILES_PATH="${AUDIO_FILES_PATH:-/app/data/audio_source}"
export UPLOADS_PATH="${UPLOADS_PATH:-/app/data/uploads}"

runtime_config_summary() {
    cat <<EOF
PROJECT_DIR=$PROJECT_DIR
COMPOSE_FILE=$COMPOSE_FILE
ENV_FILE=$ENV_FILE
PROJECT_ID=$PROJECT_ID
GIT_BRANCH=$GIT_BRANCH
HOST_DOCKER_PROJECTS=$HOST_DOCKER_PROJECTS
HOST_DOCKER_DATA=$HOST_DOCKER_DATA
HOST_BACKUPS=$HOST_BACKUPS
HOST_TRANSCRIPT_SOURCE=$HOST_TRANSCRIPT_SOURCE
HOST_AUDIO_SOURCE=$HOST_AUDIO_SOURCE
TRANSCRIPTION_PROJECTS_PATH=$TRANSCRIPTION_PROJECTS_PATH
TRANSCRIPT_SOURCE_PATH=$TRANSCRIPT_SOURCE_PATH
AUDIO_FILES_PATH=$AUDIO_FILES_PATH
UPLOADS_PATH=$UPLOADS_PATH
EOF
}