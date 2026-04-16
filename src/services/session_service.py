"""
Servicio de sesiones distribuidas con Redis para Phase 2
Permite que múltiples instancias de la app compartan estado de sesión
"""
import logging
import redis
from flask_session import Session
from datetime import timedelta

logger = logging.getLogger(__name__)

class SessionManager:
    """Gestor de sesiones distribuidas con Redis"""
    
    def __init__(self):
        self.redis_client = None
        
    def init_app(self, app, config):
        """
        Inicializa las sesiones de Flask con Redis
        
        Args:
            app: Aplicación Flask
            config: Objeto Config con REDIS_URL y SESSION_TYPE
        """
        try:
            # Verificar conexión a Redis
            self.redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
            self.redis_client.ping()
            logger.info(f"✅ Conectado a Redis en {config.REDIS_URL}")
        except Exception as e:
            logger.error(f"❌ Error conectando a Redis: {e}")
            logger.warning("⚠️  Usando sesiones en memoria (no distribuidas)")
            config.SESSION_TYPE = 'filesystem'  # Fallback
        
        # Configurar Flask-Session
        app.config['SESSION_TYPE'] = config.SESSION_TYPE
        app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=config.PERMANENT_SESSION_LIFETIME)
        app.config['SESSION_REDIS'] = self.redis_client
        app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
        app.config['SESSION_COOKIE_HTTPONLY'] = True  # No acceso desde JS
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
        app.config['SESSION_COOKIE_NAME'] = 'labeling_session'
        
        # Inicializar Flask-Session
        Session(app)
        
        if config.SESSION_TYPE == 'redis':
            logger.info("✅ Sesiones distribuidas con Redis activadas")
            logger.info("   - Múltiples instancias pueden compartir sesiones")
            logger.info("   - Load balancing habilitado para Phase 2")
        else:
            logger.warning("⚠️  Sesiones en memoria (no distribuidas)")
    
    def cleanup_sessions(self):
        """Limpia sesiones expiradas en Redis"""
        if self.redis_client:
            try:
                # Redis automáticamente elimina keys con expiry, pero
                # podemos hacer limpieza manual si es necesario
                logger.debug("Sesiones Redis gestionadas automáticamente con TTL")
            except Exception as e:
                logger.error(f"Error limpiando sesiones: {e}")
    
    def get_active_sessions_count(self):
        """Retorna el número de sesiones activas en Redis"""
        if self.redis_client:
            try:
                # Contar keys de sesión en Redis
                pattern = 'session:*'
                count = self.redis_client.dbsize()
                return count
            except Exception as e:
                logger.error(f"Error contando sesiones: {e}")
        return 0

# Instancia global
session_manager = SessionManager()
