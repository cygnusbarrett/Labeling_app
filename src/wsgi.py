"""
Archivo WSGI para ejecutar la aplicación Flask en producción de forma robusta
Entrypoint para: gunicorn -c gunicorn_config.py wsgi:app
"""
import os
import sys
import logging
import traceback
from pathlib import Path

# Configurar paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Crear directorios de logs si no existen
logs_dir = PROJECT_ROOT / 'logs'
logs_dir.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)

try:
    # Importar la aplicación
    from app import create_app
    from config import Config
    from services.health_service import HealthChecker, GracefulShutdown
    from services.database_service import DatabaseService
    
    logger.info("✅ Importaciones de módulos exitosas")
    
    # Crear la aplicación Flask
    logger.info("Inicializando aplicación Flask...")
    app, config = create_app()
    logger.info("✅ Aplicación Flask creada correctamente")
    
    # Inicializar health checker
    if config.HEALTH_CHECK_ENABLED:
        db_service = DatabaseService(config.DATABASE_URL)
        health_checker = HealthChecker(config, db_service)
        
        # Agregar endpoint de health check
        @app.route('/health', methods=['GET'])
        def health_check():
            """Endpoint de health check para monitoreo"""
            health_status = health_checker.perform_full_health_check()
            health_checker.log_alerts()
            
            from flask import jsonify
            
            status_code = 200 if health_status['overall_status'] == 'healthy' else 503
            return jsonify(health_status), status_code
        
        logger.info("✅ Health check endpoint registrado en /health")
    
    # Configurar graceful shutdown
    graceful_shutdown = GracefulShutdown()
    
    def cleanup_resources():
        """Limpia recursos antes de apagar"""
        logger.info("Limpiando recursos...")
        try:
            # Aquí agregar limpieza de recursos si es necesaria
            logger.info("✅ Recursos limpios")
        except Exception as e:
            logger.error(f"Error limpiando recursos: {e}")
    
    graceful_shutdown.register_handler(cleanup_resources)
    graceful_shutdown.setup_signal_handlers()
    
    # Configurar logging para WSGI/Gunicorn
    if __name__ != "__main__":
        # Solo configurar si estamos corriendo bajo WSGI (no en desarrollo directo)
        gunicorn_logger = logging.getLogger('gunicorn.error')
        if gunicorn_logger.handlers:
            app.logger.handlers = gunicorn_logger.handlers
            app.logger.setLevel(gunicorn_logger.level)
            logger.info("✅ Logging sincronizado con Gunicorn")
    
    logger.info(config.get_summary())
    logger.info("🟢 WSGI APP LISTO PARA PRODUCCIÓN")
    
except Exception as e:
    logger.critical(f"🔴 ERROR FATAL iniciando aplicación WSGI: {e}")
    logger.error(traceback.format_exc())
    raise


# Para desarrollo directo (cuando se ejecuta python wsgi.py)
if __name__ == "__main__":
    logger.warning("⚠️  Ejecutando en modo desarrollo directo desde wsgi.py")
    logger.warning("⚠️  Para producción, usa: gunicorn -c gunicorn_config.py wsgi:app")
    from werkzeug.serving import run_simple
    run_simple(
        hostname=config.HOST,
        port=config.PORT,
        application=app,
        use_debugger=config.DEBUG,
        use_reloader=config.DEBUG,
        threaded=True
    )
