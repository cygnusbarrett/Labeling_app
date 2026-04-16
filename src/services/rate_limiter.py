"""
Servicio de Rate Limiting para proteger endpoints en producción
Protege contra brute force, DoS, y abuso de recursos
"""
import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
from flask import request

logger = logging.getLogger(__name__)

class RateLimitService:
    """Gestor centralizado de rate limiting"""
    
    def __init__(self):
        self.limiter = Limiter(
            key_func=get_remote_address,
            strategy="fixed-window",  # Reinicia cada minuto
            storage_uri="memory://",  # Para desarrollo - cambiar a Redis en producción
            default_limits=["1000 per hour", "5000 per day"],
            swallow_errors=True  # No romper app si Redis falla
        )
    
    def init_app(self, app):
        """Inicializa el limiter con la aplicación Flask"""
        self.limiter.init_app(app)
        logger.info("✅ Rate Limiter inicializado")
    
    def get_limiter(self):
        """Retorna la instancia del limitador"""
        return self.limiter
    
    # Métodos para aplicar límites a rutas específicas
    def limit_submit(self, f):
        """Limita submisiones: 60 por minuto"""
        return self.limiter.limit("60 per minute")(f)
    
    def limit_api_call(self, f):
        """Limita llamadas API: 100 por minuto"""
        return self.limiter.limit("100 per minute")(f)
    
    def limit_login(self, f):
        """Limita intentos de login: 5 por 15 minutos"""
        return self.limiter.limit("5 per 15 minutes")(f)


# Instancia global
rate_limit_service = RateLimitService()

# Decoradores de conveniencia (deprecated - usar métodos del service)
def limit_login(f):
    """Limita intentos de login: 5 por 15 minutos"""
    return rate_limit_service.limit_login(f)

def limit_api_call(f):
    """Limita llamadas API: 100 por minuto por IP"""
    return rate_limit_service.limit_api_call(f)

def limit_submit(f):
    """Limita submisiones: 60 por minuto (normal workflow)"""
    return rate_limit_service.limit_submit(f)
