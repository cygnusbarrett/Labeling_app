#!/bin/bash
# rotate_keys.sh - Script para rotación segura de claves secretas

set -e  # Salir en caso de error

echo "🔄 ROTACIÓN DE CLAVES SECRETAS"
echo "================================"

# Verificar que estamos en el directorio correcto
if [ ! -f "envs/web_app.env" ]; then
    echo "❌ Error: Archivo envs/web_app.env no encontrado"
    exit 1
fi

# Crear backup
BACKUP_FILE="envs/web_app.env.backup.$(date +%Y%m%d_%H%M%S)"
cp envs/web_app.env "$BACKUP_FILE"
echo "📦 Backup creado: $BACKUP_FILE"

# Generar nuevas claves
echo "🔐 Generando nuevas claves..."
NEW_JWT_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
NEW_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Actualizar archivo .env
sed -i.bak "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$NEW_JWT_KEY/" envs/web_app.env
sed -i.bak "s/SECRET_KEY=.*/SECRET_KEY=$NEW_SECRET_KEY/" envs/web_app.env

# Limpiar archivos temporales de sed
rm -f envs/web_app.env.bak

echo "✅ Claves actualizadas exitosamente"
echo ""
echo "📋 Nuevas claves generadas:"
echo "JWT_SECRET_KEY: ${NEW_JWT_KEY:0:20}..."
echo "SECRET_KEY: ${NEW_SECRET_KEY:0:20}..."
echo ""
echo "⚠️  IMPORTANTE:"
echo "1. Reinicia la aplicación para aplicar cambios"
echo "2. Los tokens JWT existentes serán invalidados"
echo "3. Notifica a los usuarios sobre la rotación"
echo ""
echo "🔄 Comando para reiniciar:"
echo "sudo systemctl restart labeling-app"