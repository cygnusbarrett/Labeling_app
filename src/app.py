"""
Aplicación Flask para validación colaborativa de transcripciones de audio con JWT Auth
"""
from flask import Flask, render_template, send_from_directory, session, redirect, request, jsonify
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
from routes.admin_api_routes import admin_bp
from models.database import DatabaseManager, User
from services.rate_limiter import rate_limit_service
from services.session_service import session_manager

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

def create_app():
    """Factory para crear la aplicación Flask de transcripciones de audio con JWT"""
    # Configurar rutas de templates y static
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__, 
                template_folder=os.path.join(current_dir, 'templates'),
                static_folder=os.path.join(current_dir, 'static'))
    
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
    
    # Inicializar Rate Limiting para proteger endpoints
    rate_limit_service.init_app(app)
    logger.info("✅ Rate Limiting inicializado")
    
    # Inicializar sesiones distribuidas con Redis (Phase 2)
    session_manager.init_app(app, config)
    logger.info("✅ Sesiones distribuidas inicializadas")
    
    # Registrar blueprints
    app.register_blueprint(transcription_bp)
    logger.debug("Blueprint de API de transcripción registrado")
    
    app.register_blueprint(admin_bp)
    logger.debug("Blueprint de API administrativo registrado")
    
    # Importar decoradores de autenticación
    from services.jwt_service import optional_jwt, require_admin, require_auth, jwt_service
    
    # Rutas principales
    @app.route('/')
    def index():
        """Página principal - redirige a login si no está autenticado"""
        logger.debug("Acceso a página principal")
        try:
            token = jwt_service.get_token_from_cookie_or_header()
            if token:
                payload = jwt_service.verify_access_token(token)
                logger.debug(f"Usuario autenticado: {payload.get('username')}")
                return redirect('/transcription/validator')
        except Exception as e:
            logger.debug(f"Token inválido: {e}")
        
        return redirect('/login')
    
    @app.route('/login')
    def login_page():
        """Página de login"""
        logger.debug("Acceso a página de login")
        return render_template('sqlite_login.html')
    
    @app.route('/transcription/validator')
    @require_auth
    def transcription_validator():
        """Página de validador de transcripciones"""
        logger.debug("Acceso a página de validador de transcripciones")
        logger.info(f"Usuario autenticado accediendo a validador: {request.current_user['username']}")
        
        return render_template('transcription_validator.html')
    
    @app.route('/admin')
    def admin_page():
        """Página de administración"""
        logger.debug("Acceso a página de administración")
        try:
            token = jwt_service.get_token_from_cookie_or_header()
            if not token:
                logger.warning("Admin access denied - no token")
                return redirect('/login')
            
            payload = jwt_service.verify_access_token(token)
            if payload.get('role') != 'admin':
                logger.warning(f"Admin access denied - user {payload.get('username')} is not admin")
                return redirect('/login')
            
            logger.info(f"Admin access granted to {payload.get('username')}")
            return redirect('/admin/dashboard')
            
        except Exception as e:
            logger.warning(f"Admin access denied - invalid token: {e}")
            return redirect('/login')
    
    @app.route('/admin/dashboard')
    def admin_dashboard():
        """Dashboard administrativo de Phase 2 - Gestión de usuarios, asignaciones y control de calidad"""
        logger.debug("Acceso a dashboard administrativo")
        try:
            token = jwt_service.get_token_from_cookie_or_header()
            if not token:
                logger.warning("Admin dashboard access denied - no token")
                return redirect('/login')
            
            payload = jwt_service.verify_access_token(token)
            if payload.get('role') != 'admin':
                logger.warning(f"Admin dashboard access denied - user {payload.get('username')} is not admin")
                return redirect('/transcription/validator')
            
            logger.info(f"Admin dashboard access granted to {payload.get('username')}")
            return render_template('admin_dashboard.html')
            
        except Exception as e:
            logger.warning(f"Admin dashboard access denied - invalid token: {e}")
            return redirect('/login')
    
    # ==================== RUTAS DE AUTENTICACIÓN ====================
    
    @app.route('/login', methods=['POST'])
    @rate_limit_service.limit_login
    def login():
        """Autentica usuario y retorna JWT token"""
        logger.info("=" * 80)
        logger.info("🔐 POST /login RECIBIDO")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Remote Address: {request.remote_addr}")
        logger.info(f"User-Agent: {request.headers.get('User-Agent', 'N/A')}")
        
        try:
            logger.info(f"📦 Raw body data: {request.data[:200]}")
            
            data = request.get_json(force=True, silent=True)
            logger.info(f"📋 JSON parsed successfully: {data}")
            
            if not data:
                logger.error("❌ No se pudo parsear JSON")
                return jsonify({'error': 'Invalid JSON format', 'success': False}), 400
            
            username = data.get('username', '').strip() if data else ''
            password = data.get('password', '') if data else ''
            
            logger.info(f"👤 Username recibido: '{username}' (longitud={len(username)})")
            logger.info(f"🔑 Password recibido: {'*' * min(len(password), 8) if password else 'EMPTY'} (longitud={len(password)})")
            
            if not username or not password:
                logger.warning("⚠️  Credenciales incompletas")
                return jsonify({
                    'error': 'Usuario y contraseña requeridos',
                    'success': False,
                    'debug': {'username': bool(username), 'password': bool(password)}
                }), 400
            
            logger.info(f"🔍 Buscando usuario en BD: '{username}'")
            db_manager = DatabaseManager(config.DATABASE_URL)
            session = db_manager.get_session()
            
            user = session.query(User).filter_by(username=username).first()
            logger.info(f"📊 Usuario encontrado en BD: {user is not None}")
            
            if user:
                logger.info(f"   └─ ID: {user.id}")
                logger.info(f"   └─ Username: {user.username}")
                logger.info(f"   └─ Role: {user.role}")
                logger.info(f"🔐 Verificando hash de contraseña...")
                pwd_valid = user.check_password(password)
                logger.info(f"   └─ Contraseña válida: {pwd_valid}")
                if not pwd_valid:
                    logger.warning(f"   └─ ❌ Hash no coincide con password proporcionado")
            else:
                logger.warning(f"   └─ ❌ Usuario NO encontrado en BD")
            
            session.close()
            
            if not user or not user.check_password(password):
                logger.warning(f"❌ LOGIN FALLIDO para usuario: {username}")
                return jsonify({
                    'error': 'Usuario o contraseña incorrectos',
                    'success': False
                }), 401
            
            # Generar tokens JWT
            logger.info(f"✅ LOGIN EXITOSO - Generando tokens JWT para: {user.username} (ID: {user.id})")
            access_token = jwt_service.create_access_token(user.id, user.username, user.role)
            refresh_token = jwt_service.create_refresh_token(user.id)
            
            response_data = {
                'success': True,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role
                },
                'expires_in': config.JWT_ACCESS_TOKEN_EXPIRES * 60
            }
            
            logger.info(f"✅ Tokens generados correctamente")
            logger.info(f"   └─ Access token length: {len(access_token)} chars")
            logger.info(f"   └─ Refresh token length: {len(refresh_token)} chars")
            logger.info("=" * 80)
            
            return jsonify(response_data), 200
            
        except Exception as e:
            logger.error(f"❌ EXCEPCIÓN en POST /login: {str(e)}", exc_info=True)
            logger.error(f"   └─ Tipo: {type(e).__name__}")
            logger.error("=" * 80)
            return jsonify({
                'error': f'Error interno del servidor: {str(e)}',
                'success': False
            }), 500
    
    @app.route('/logout', methods=['POST'])
    def logout():
        """Cierra sesión del usuario"""
        logger.info("User logged out")
        return jsonify({'message': 'Logged out successfully'}), 200
    
    @app.route('/me', methods=['GET'])
    def get_current_user():
        """Retorna datos del usuario autenticado"""
        try:
            token = jwt_service.get_token_from_cookie_or_header()
            if not token:
                logger.debug("GET /me - No token provided")
                return jsonify({'error': 'No token provided'}), 401
            
            payload = jwt_service.verify_access_token(token)
            
            db_manager = DatabaseManager(config.DATABASE_URL)
            session = db_manager.get_session()
            user = session.query(User).filter_by(id=payload.get('user_id')).first()
            session.close()
            
            if not user:
                logger.warning(f"GET /me - User not found: {payload.get('user_id')}")
                return jsonify({'error': 'User not found'}), 404
            
            logger.debug(f"GET /me - Retrieved user: {user.username}")
            
            return jsonify({
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error en GET /me: {str(e)}")
            return jsonify({'error': 'Authentication failed'}), 401
    
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
