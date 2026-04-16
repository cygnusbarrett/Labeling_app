#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# PRODUCTION DEPLOYMENT SCRIPT
# Automatiza el setup y deployment de la aplicación en producción
# ═══════════════════════════════════════════════════════════════════════════

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
DOCKER_COMPOSE="docker-compose -f $PROJECT_DIR/docker-compose.prod.yml"

# Funciones
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# ═══════════════════════════════════════════════════════════════════════════

print_header "PRODUCTION DEPLOYMENT"

# Paso 1: Verificar requisitos
print_header "Step 1: Verificar requisitos"

if ! command -v docker &> /dev/null; then
    print_error "Docker no está instalado"
    exit 1
fi
print_success "Docker instalado"

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose no está instalado"
    exit 1
fi
print_success "Docker Compose instalado"

# Paso 2: Verificar directorios y permisos
print_header "Step 2: Verificar directorios"

# Crear directorios necesarios
mkdir -p "$PROJECT_DIR/certs"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/src/logs"
mkdir -p "$PROJECT_DIR/data/backups"
print_success "Directorios verificados/creados"

# Paso 3: Verificar .env
print_header "Step 3: Configuración de entorno"

if [ ! -f "$ENV_FILE" ]; then
    print_warning ".env no encontrado, copiando desde .env.production"
    cp "$PROJECT_DIR/.env.production" "$ENV_FILE"
    print_warning "⚠  IMPORTANTE: Edita .env con valores seguros antes de continuar"
    
    read -p "¿Has editado .env con valores de producción? (s/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        print_error "Por favor edita .env primero"
        exit 1
    fi
fi
print_success ".env configurado"

# Paso 4: Verificar SSL certificates
print_header "Step 4: Verificar certificados SSL"

if [ ! -f "$PROJECT_DIR/certs/cert.pem" ] || [ ! -f "$PROJECT_DIR/certs/key.pem" ]; then
    print_warning "Certificados SSL no encontrados, generando autofirmados..."
    
    mkdir -p "$PROJECT_DIR/certs"
    cd "$PROJECT_DIR/certs"
    
    openssl req -x509 -newkey rsa:2048 \
        -keyout key.pem \
        -out cert.pem \
        -days 365 \
        -nodes \
        -subj "/C=ES/ST=Madrid/L=Madrid/O=NuestraMemoria/CN=localhost"
    
    print_success "Certificados generados: cert.pem, key.pem"
    print_warning "⚠  Para producción usa Let's Encrypt o certificados reales"
else
    print_success "Certificados SSL encontrados"
fi

# Paso 5: Build imágenes Docker
print_header "Step 5: Build Docker images"

echo "Building images (esto puede tomar 2-3 minutos)..."
$DOCKER_COMPOSE build --no-cache

print_success "Docker images construidas"

# Paso 6: Detener contenedores anteriores
print_header "Step 6: Limpieza de contenedores anteriores"

$DOCKER_COMPOSE down || true
print_success "Contenedores anteriores detenidos"

# Paso 7: Iniciar servicios
print_header "Step 7: Iniciando servicios"

$DOCKER_COMPOSE up -d

print_success "Servicios iniciados"

# Paso 8: Esperar a que servicios estén healthy
print_header "Step 8: Esperando servicios (60 segundos)..."

sleep 10
ATTEMPT=0
MAX_ATTEMPTS=12

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if $DOCKER_COMPOSE ps | grep -q "healthy"; then
        print_success "Servicios están healthy"
        break
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        print_error "Timeout esperando servicios. Ver logs con: docker-compose logs -f"
        exit 1
    fi
    
    echo "Intento $ATTEMPT/$MAX_ATTEMPTS... esperando..."
    sleep 5
done

# Paso 9: Verificar status
print_header "Step 9: Verificar status"

$DOCKER_COMPOSE ps

# Paso 10: Verificar conectividad
print_header "Step 10: Verificaciones finales"

echo "Esperando que Nginx esté listo..."
sleep 5

# Exportar PORT del .env
export $(cat "$ENV_FILE" | grep -v '#' | xargs)

# Verificar endpoints
if curl -s -k https://localhost:3000/login > /dev/null 2>&1; then
    print_success "✓ Flask respondiendo en https://localhost:3000"
else
    print_warning "⚠  Flask no responde aún, revisar logs"
fi

if curl -s http://localhost/health > /dev/null 2>&1; then
    print_success "✓ Nginx health check OK"
else
    print_warning "⚠  Nginx no responde, revisar logs"
fi

# ═══════════════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ═══════════════════════════════════════════════════════════════════════════

print_header "DEPLOYMENT COMPLETADO ✓"

echo ""
echo "📊 SERVICIOS ACTIVOS:"
echo "  • PostgreSQL: localhost:5432"
echo "  • Redis: localhost:6379"
echo "  • Flask: localhost:3000"
echo "  • Nginx (HTTP): http://localhost:80"
echo "  • Nginx (HTTPS): https://localhost:443"
echo "  • PgAdmin: http://localhost:5050"
echo ""
echo "🔍 COMANDOS ÚTILES:"
echo "  Ver logs:           docker-compose -f docker-compose.prod.yml logs -f"
echo "  Ver logs Flask:     docker-compose -f docker-compose.prod.yml logs -f web_app"
echo "  Ver logs Nginx:     docker-compose -f docker-compose.prod.yml logs -f nginx"
echo "  Detener servicios:  docker-compose -f docker-compose.prod.yml down"
echo "  Ver status:         docker-compose -f docker-compose.prod.yml ps"
echo "  Escalar Flask:      docker-compose -f docker-compose.prod.yml up --scale web_app=3"
echo ""
echo "🔐 CONFIGURACIÓN:"
echo "  Archivo .env actualizado: $ENV_FILE"
echo "  Puerto HTTP: 80 → HTTPS 443 → Flask 3000"
echo "  Certificados: $PROJECT_DIR/certs/"
echo ""
echo "📖 VER DOCUMENTACIÓN:"
echo "  • DEPLOYMENT_DOCKER_SETUP.md - Guía completa"
echo "  • DEPLOYMENT_PRODUCTION.md - Detalles adicionales"
echo "  • KEY_MANAGEMENT.md - Gestión de secretos"
echo ""

print_success "¡Deployment listo!"
