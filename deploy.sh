#!/bin/bash

################################################################################
# DEPLOY SCRIPT - Automatizar instalación en servidor remoto
# Uso: ./deploy.sh --server user@host --env production
################################################################################

set -eo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuración por defecto
DEPLOY_USER="${DEPLOY_USER:-labeling}"
DEPLOY_GROUP="${DEPLOY_GROUP:-labeling}"
APP_ROOT="/opt/labeling_app"
APP_DIR="$APP_ROOT/src"
ENV_FILE="/etc/labeling_app/production.env"

# Funciones
log_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}✓ ${NC}$1"
}

log_warning() {
    echo -e "${YELLOW}⚠ ${NC}$1"
}

log_error() {
    echo -e "${RED}✗ ${NC}$1"
}

usage() {
    cat <<EOF
Uso: $0 [opciones]

Opciones:
    --server USER@HOST      Servidor remoto (SSH)
    --env FILE              Archivo .env con configuración
    --help                  Mostrar esta ayuda

Ejemplo:
    $0 --server ubuntu@my-server.com --env .env.production
EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server) REMOTE_SERVER="$2"; shift 2 ;;
        --env) ENV_FILE="$2"; shift 2 ;;
        --help) usage ;;
        *) log_error "Opción desconocida: $1"; usage ;;
    esac
done

if [[ -z "$REMOTE_SERVER" ]]; then
    log_error "Debe especificar --server"
    usage
fi

if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Archivo .env no encontrado: $ENV_FILE"
    exit 1
fi

################################################################################
# EJECUCIÓN EN SERVIDOR REMOTO
################################################################################

REMOTE_SCRIPT='
#!/bin/bash
set -eo pipefail

### Configuración
APP_ROOT="/opt/labeling_app"
APP_DIR="$APP_ROOT/src"
VENV_DIR="$APP_ROOT/venv"
DEPLOY_USER="labeling"
DEPLOY_GROUP="labeling"

### Colores
GREEN="\\033[0;32m"
BLUE="\\033[0;34m"
NC="\\033[0m"

log_info() { echo -e "${BLUE}ℹ ${NC}$1"; }
log_success() { echo -e "${GREEN}✓ ${NC}$1"; }

### PASO 1: Validar entorno
log_info "Validando entorno..."
if ! command -v python3 &> /dev/null; then
    echo "Python3 no instalado. Instala con: sudo apt install python3.10"
    exit 1
fi

if ! command -v psql &> /dev/null; then
    echo "PostgreSQL no instalado. Instala con: sudo apt install postgresql"
    exit 1
fi

if ! command -v nginx &> /dev/null; then
    echo "Nginx no instalado. Instala con: sudo apt install nginx"
    exit 1
fi

log_success "Entorno validado"

### PASO 2: Crear usuario si no existe
log_info "Verificando usuario de aplicación..."
if ! id "$DEPLOY_USER" &>/dev/null; then
    sudo useradd -r -s /bin/bash -d "$APP_ROOT" "$DEPLOY_USER"
    log_success "Usuario $DEPLOY_USER creado"
else
    log_success "Usuario $DEPLOY_USER ya existe"
fi

### PASO 3: Crear directorios
log_info "Creando directorios..."
sudo mkdir -p "$APP_ROOT" /var/log/labeling_app /etc/labeling_app
sudo chown -R "$DEPLOY_USER:$DEPLOY_GROUP" "$APP_ROOT" /var/log/labeling_app
sudo chmod 755 "$APP_ROOT"
log_success "Directorios creados"

### PASO 4: Virtual environment
log_info "Configurando Virtual Environment..."
if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
    log_success "Virtual Environment creado"
fi

# Activar venv
source "$VENV_DIR/bin/activate"

### PASO 5: Instalar dependencias
log_info "Instalando dependencias..."
pip install --upgrade pip setuptools wheel
pip install -q -r "$APP_DIR/requirements/requirements.txt"
pip install -q gunicorn psycopg2-binary psutil
log_success "Dependencias instaladas"

### PASO 6: Test de importación
log_info "Validando módulos..."
cd "$APP_DIR"
python3 -c "from app import create_app; print("✓ App module valid")" || exit 1
log_success "Módulos validados"

### PASO 7: Crear servicio systemd
log_info "Configurando servicio systemd..."
sudo cp "$APP_DIR/../labeling-app.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable labeling-app
log_success "Servicio systemd habilitado"

### PASO 8: Verificar BD
log_info "Verificando conexión a PostgreSQL..."
if ! psql -U labeling_user -d labeling_db -h localhost -c "SELECT 1" >/dev/null 2>&1; then
    echo "⚠️ No se puede conectar a la BD. Crea la BD con DEPLOYMENT.md Paso 4"
else
    log_success "Conexión a BD exitosa"
fi

### PASO 9: Iniciar servicio
log_info "Iniciando servicio..."
sudo systemctl restart labeling-app
sleep 2

if sudo systemctl is-active --quiet labeling-app; then
    log_success "Servicio iniciado exitosamente"
else
    echo "Error: Servicio no levantó. Ver logs con: journalctl -u labeling-app -n 50"
    exit 1
fi

### PASO 10: Verificar salud
log_info "Verificando salud de la aplicación..."
sleep 3
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    log_success "Health check exitoso"
else
    log_success "App levantada (health check aún cargando)"
fi

### Resumen
cat <<EOF

╔════════════════════════════════════════════════════════╗
║         ✅ DEPLOYMENT COMPLETADO EXITOSAMENTE          ║
╚════════════════════════════════════════════════════════╝

Ubicación:      $APP_ROOT
Logs:           journalctl -u labeling-app -f
Configuración:  $ENV_FILE
Servicio:       sudo systemctl status labeling-app

Próximos pasos:
  1. Configura Nginx (ver DEPLOYMENT.md)
  2. Obtén certificado SSL con certbot
  3. Verifica con: curl https://tu-dominio.com/health
  4. Configura backups automáticos

EOF
'

################################################################################
# EJECUTAR EN SERVIDOR
################################################################################

log_info "Conectando a servidor: $REMOTE_SERVER"

# Copiar .env
log_info "Copiando configuración..."
scp "$ENV_FILE" "$REMOTE_SERVER:/tmp/production.env"

# Ejecutar script
ssh "$REMOTE_SERVER" <<EOFREMOTE
$REMOTE_SCRIPT

# Copiar .env a ubicación final
echo "ℹ Moviendo configuración..."
sudo mv /tmp/production.env "$ENV_FILE"
sudo chmod 600 "$ENV_FILE"
sudo chown $DEPLOY_USER:$DEPLOY_GROUP "$ENV_FILE"
EOFREMOTE

log_success "¡Deployment completado!"
log_info "Próximo paso: Configura Nginx y SSL según DEPLOYMENT.md"
