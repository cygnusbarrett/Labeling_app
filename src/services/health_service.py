"""
Servicio de salud de la aplicación - monitoreo 24/7 para servidor remoto
Verifica estado de base de datos, recursos del sistema y conectividad
"""
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

# Imports opcionales con fallback
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

try:
    from sqlalchemy import text
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    text = None

logger = logging.getLogger(__name__)

class HealthChecker:
    """Monitor de salud integral para la aplicación"""
    
    def __init__(self, config, db_service):
        self.config = config
        self.db_service = db_service
        self.last_check = None
        self.check_history = []
        self.alerts = []
    
    def check_database_health(self) -> Dict:
        """Verifica salud de la base de datos"""
        if not SQLALCHEMY_AVAILABLE:
            return {
                'status': 'error',
                'error': 'SQLAlchemy no disponible',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            start_time = time.time()
            session = self.db_service.get_session()
            
            # Simple query para verificar conexión
            result = session.execute(text("SELECT 1"))
            session.close()
            
            response_time = time.time() - start_time
            
            # Alertas por latencia
            if response_time > 5:
                self.alerts.append(f"⚠️ DB SLOW: Respuesta tardía ({response_time:.2f}s)")
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time * 1000,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.alerts.append(f"🔴 DB ERROR: {str(e)}")
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_disk_health(self) -> Dict:
        """Verifica espacio en disco disponible"""
        if not PSUTIL_AVAILABLE:
            return {
                'status': 'unavailable',
                'error': 'psutil no disponible',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            disk_usage = psutil.disk_usage('/')
            free_bytes = disk_usage.free
            
            warning_threshold = self.config.DISK_SPACE_WARNING_THRESHOLD
            
            if free_bytes < warning_threshold:
                self.alerts.append(
                    f"⚠️ BAJO ESPACIO EN DISCO: {free_bytes / (1024**3):.2f}GB libre"
                )
            
            return {
                'status': 'healthy' if free_bytes > warning_threshold else 'warning',
                'total_gb': disk_usage.total / (1024**3),
                'used_gb': disk_usage.used / (1024**3),
                'free_gb': disk_usage.free / (1024**3),
                'percent_used': disk_usage.percent,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Disk health check failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_memory_health(self) -> Dict:
        """Verifica uso de memoria"""
        if not PSUTIL_AVAILABLE:
            return {
                'status': 'unavailable',
                'error': 'psutil no disponible',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            memory = psutil.virtual_memory()
            
            # Alerta si memoria > 80%
            if memory.percent > 80:
                self.alerts.append(f"⚠️ MEMORIA ALTA: {memory.percent}% en uso")
            
            return {
                'status': 'healthy' if memory.percent < 85 else 'warning',
                'total_gb': memory.total / (1024**3),
                'used_gb': memory.used / (1024**3),
                'available_gb': memory.available / (1024**3),
                'percent_used': memory.percent,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Memory health check failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_cpu_health(self) -> Dict:
        """Verifica uso de CPU"""
        if not PSUTIL_AVAILABLE:
            return {
                'status': 'unavailable',
                'error': 'psutil no disponible',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else None
            
            # Alerta si CPU > 85%
            if cpu_percent > 85:
                self.alerts.append(f"⚠️ CPU ALTA: {cpu_percent}% en uso")
            
            return {
                'status': 'healthy' if cpu_percent < 90 else 'warning',
                'percent_used': cpu_percent,
                'core_count': psutil.cpu_count(),
                'load_average': {
                    '1min': load_avg[0] if load_avg else None,
                    '5min': load_avg[1] if load_avg else None,
                    '15min': load_avg[2] if load_avg else None,
                } if load_avg else None,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"CPU health check failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def perform_full_health_check(self) -> Dict:
        """Ejecuta chequeo completo de salud"""
        self.alerts = []  # Limpiar alertas previas
        
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'database': self.check_database_health(),
            'disk': self.check_disk_health(),
            'memory': self.check_memory_health(),
            'cpu': self.check_cpu_health(),
            'alerts': self.alerts,
            'overall_status': 'healthy'
        }
        
        # Determinar estado general
        if any(check.get('status') == 'unhealthy' for check in [
            health_report['database'],
            health_report['disk'],
            health_report['memory'],
            health_report['cpu']
        ]):
            health_report['overall_status'] = 'unhealthy'
        elif self.alerts:
            health_report['overall_status'] = 'warning'
        
        # Guardar en historial
        self.check_history.append(health_report)
        self.last_check = health_report
        
        # Mantener solo últimos 100 chequeos
        if len(self.check_history) > 100:
            self.check_history = self.check_history[-100:]
        
        return health_report
    
    def log_alerts(self):
        """Registra alertas en el logger"""
        if self.alerts:
            logger.warning(f"🚨 ALERTAS DE SALUD: {len(self.alerts)} problemas detectados")
            for alert in self.alerts:
                logger.warning(f"   {alert}")
    
    def get_health_status(self) -> Dict:
        """Obtiene estado actual de salud"""
        if not self.last_check:
            return self.perform_full_health_check()
        return self.last_check
    
    def get_health_history(self, limit: int = 10) -> list:
        """Obtiene historial de chequeos de salud"""
        return self.check_history[-limit:]


class RetryHelper:
    """Helper para reintentos con backoff exponencial"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def execute_with_retry(self, func, *args, **kwargs):
        """Ejecuta función con reintentos y backoff exponencial"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Intento {attempt + 1}/{self.max_retries} de {func.__name__}")
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)  # Backoff exponencial
                    logger.warning(
                        f"Error en {func.__name__} (intento {attempt + 1}): {str(e)}. "
                        f"Reintentando en {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Fallaron todos los reintentos para {func.__name__}: {str(e)}"
                    )
        
        raise last_exception


class GracefulShutdown:
    """Manejador de shutdown graceful con limpieza de recursos"""
    
    def __init__(self):
        self.shutdown_event = False
        self.shutdown_handlers = []
    
    def register_handler(self, handler):
        """Registra un handler para ejecutar en shutdown"""
        self.shutdown_handlers.append(handler)
    
    def trigger_shutdown(self, signum=None, frame=None):
        """Dispara shutdown graceful"""
        logger.info("🛑 Iniciando shutdown graceful...")
        self.shutdown_event = True
        
        for handler in self.shutdown_handlers:
            try:
                logger.info(f"Ejecutando: {handler.__name__}")
                handler()
            except Exception as e:
                logger.error(f"Error en shutdown handler {handler.__name__}: {e}")
        
        logger.info("✅ Shutdown completado")
    
    def setup_signal_handlers(self):
        """Configura manejadores de señales para shutdown graceful"""
        import signal
        
        signal.signal(signal.SIGTERM, self.trigger_shutdown)
        signal.signal(signal.SIGINT, self.trigger_shutdown)
        
        logger.info("Signal handlers para SIGTERM/SIGINT configurados")
