"""
""""""
from flask import Flask, render_template, send_from_directory, session, redirect, request
import os
import logging
from pathlib import Path

# Cargar variables de entorno desde archivo .env
env_file = Path(__file__).parent.parent / 'envs' / 'web_app.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

from config import Config
from routes.transcription_api_routes import transcription_bp
from models.database import DatabaseManager

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

def create_app():
    """Factory para crear la aplicación Flask de transcripciones de audio con JWT"""
    app = Flask(__name__)
    
    # Cargar configuración
    config = Config.from_env()

    # Validar configuración en producción
    if config.is_production():
        config.validate_production_config()
    
    # Configuración JWT mejorada
    if config.JWT_SECRET_KEY:
        app.config['JWT_SECRET_KEY'] = config.JWT_SECRET_KEY
    else:
        if config.is_production():
            raise ValueError("JWT_SECRET_KEY es obligatorio en producción")
        else:
            # Solo para desarrollo - generar clave temporal
            app.config['JWT_SECRET_KEY'] = os.urandom(32).hex()
            logger.warning("⚠️  Usando JWT_SECRET_KEY temporal para desarrollo")
    
    # Flask session secret
    if config.SECRET_KEY:
        app.secret_key = config.SECRET_KEY
    else:
        if config.is_production():
            raise ValueError("SECRET_KEY es obligatorio en producción")
        else:
            app.secret_key = 'dev-secret-key-change-in-production'
            logger.warning("⚠️  Usando SECRET_KEY temporal para desarrollo")

    # Configurar logging
    config.setup_logging()
    logger.info("Iniciando aplicación Flask con JWT Auth")
    
    # Configuración JWT
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = config.JWT_ACCESS_TOKEN_EXPIRES
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = config.JWT_REFRESH_TOKEN_EXPIRES
    logger.debug(f"JWT configurado - Access token: {config.JWT_ACCESS_TOKEN_EXPIRES}min, Refresh: {config.JWT_REFRESH_TOKEN_EXPIRES}días")
    
    app.config["DATABASE_URL"] = config.DATABASE_URL  
    # Inicializar base de datos
    logger.info("Inicializando base de datos")
    db_manager = DatabaseManager(config.DATABASE_URL)
    db_manager.create_tables()
    db_manager.init_admin_user()
    logger.info("Base de datos inicializada correctamente")
    
    # Registrar blueprints
    app.register_blueprint(transcription_bp)
    logger.debug("Blueprint de API de transcripción registrado")
    
    # Importar decoradores de autenticación
    from services.jwt_service import optional_auth, require_admin, require_auth
    
    # Rutas principales
    @app.route('/')
    @require_auth
    def index():
        """Página principal - redirige a validador de transcripciones"""
        logger.debug("Redirigiendo a página de transcripciones")
        return redirect('/transcription/validator')
    
    @app.route('/login')
    @optional_auth
    def login_page():
        """Página de login - redirige si ya está autenticado"""
        logger.debug("Acceso a página de login")
        
        return render_template('sqlite_login.html')
    
    @app.route('/transcription/validator')
    def transcription_validator():
        """Página de validador de transcripciones"""
        logger.debug("Acceso a página de validador de transcripciones")
        
        return render_template('transcription_validator.html')
    
    @app.route('/admin')
    @require_admin
    def admin_page():
        """Página de administración - redirige a transcripciones (funcionalidad limitada)"""
        logger.debug("Acceso a página de administración - redirigiendo a transcripciones")
        
        user = request.current_user
        logger.info(f"Acceso concedido a panel admin para usuario {user.get('username')}")
        # Por ahora, redirigir a la página de transcripciones
        # TODO: Crear página de administración específica para transcripciones
        return redirect('/transcription/validator')
    
    @app.route('/favicon.ico')
    def favicon():
        """Serve favicon to avoid 404s"""
        try:
            return send_from_directory(os.path.join(app.root_path, 'static', 'icons'), 'favicon.svg', mimetype='image/svg+xml')
        except Exception:
            # Fallback: 204 No Content to avoid log noise if file missing
            from flask import Response
            return Response(status=204)
    
    # Información de inicio
    logger.info("=== Aplicación de Transcripciones de Audio iniciada ===")
    logger.info(f"Servidor: http://localhost:{config.PORT}")
    logger.info(f"Base de datos: labeling_app.db")
    logger.info(f"Autenticación: JWT (tokens)")
    logger.info(f"Log Level: {config.LOG_LEVEL}")
    logger.info("Credenciales por defecto: Admin: admin / admin123")
    logger.info("Accede a: /transcription/validator")
    logger.info("===========================================")
    
    return app, config

if __name__ == '__main__':
    try:
        logger.info("Iniciando aplicación desde main")
        app, config = create_app()
        logger.info(f"Ejecutando servidor en {config.HOST}:{config.PORT} (debug={config.DEBUG})")
        app.run(
            debug=config.DEBUG, 
            host=config.HOST, 
            port=config.PORT
        )
    except Exception as e:
        logger.critical(f"Error crítico iniciando la aplicación: {e}")
        import traceback
        logger.error(traceback.format_exc())
