#!/bin/bash
# Script para configurar backups automáticos con cron
# Uso: bash setup_backups.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/data/backups"

echo "🔧 Configurando backups automáticos"
echo "   Script: $SCRIPT_DIR/backup_service.py"
echo "   Directorio: $BACKUP_DIR"

# Crear directorio de backups
mkdir -p "$BACKUP_DIR"
chmod 755 "$BACKUP_DIR"

# Crear archivo de log
CRON_LOG="$BACKUP_DIR/cron.log"
touch "$CRON_LOG"
chmod 666 "$CRON_LOG"

# Generar cron job
CRON_JOB="0 * * * * cd $PROJECT_DIR && . venv/bin/activate && python src/services/backup_service.py >> $CRON_LOG 2>&1"

echo ""
echo "📋 Cron job a instalar:"
echo "   $CRON_JOB"
echo ""

# Verificar si ya existe en crontab
if crontab -l 2>/dev/null | grep -q "backup_service.py"; then
    echo "⚠️  Job ya existe en crontab"
else
    # Agregar a crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Job agregado a crontab (cada hora)"
fi

# Mostrar backups actuales
echo ""
echo "📊 Estado actual:"
python "$SCRIPT_DIR/backup_service.py" list || echo "No hay backups aún"

echo ""
echo "✅ Setup completado"
echo ""
echo "💡 Comandos útiles:"
echo "   Ver crontab: crontab -l"
echo "   Ver logs: tail -f $CRON_LOG"
echo "   Hacer backup manual: python $SCRIPT_DIR/backup_service.py"
echo "   Listar backups: python $SCRIPT_DIR/backup_service.py list"
