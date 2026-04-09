"""
Configuración de la aplicación con robustez para servidor remoto 24/7
"""
import os
import logging
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    # Rutas de archivos - CONFIGURABLES PARA SERVIDOR REMOTO
    TRANSCRIPTION_PROJECTS_PATH: str = "data/transcription_projects"  # ← Configurable
    AUDIO_FILES_PATH: str = "data/audio_files"  # ← Para archivos de audio adicionales
    UPLOADS_PATH: str = "data/uploads"  # ← Para archivos subidos
    
    # Configuración de guardado
    AUTOSAVE_INTERVAL: int = 10  # Guardar cada N imágenes
    
    # Configuración de guardado
    AUTOSAVE_INTERVAL: int = 10  # Guardar cada N imágenes
    
    # Configuración del servidor
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    WORKERS: int = 4  # Para Gunicorn en producción
    WORKER_TIMEOUT: int = 120  # segundos
    WORKER_CLASS: str = "sync"  # o "gevent" para más concurrencia
    
    # Configuración de seguridad JWT
    JWT_SECRET_KEY: str = None
    JWT_ACCESS_TOKEN_EXPIRES: int = 60  # minutos (1 hora)
    JWT_REFRESH_TOKEN_EXPIRES: int = 30  # días
    
    # Flask session secret
    FLASK_ENV: str = "development"  # development, production
    SECRET_KEY: str = None
    
    # Configuración de logging
    LOG_PATH: str = "logs/"
    LOG_LEVEL: str = "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = os.path.join(LOG_PATH, "app.log")
    LOG_MAX_BYTES: int = 50 * 1024 * 1024  # 50MB para producción
    LOG_BACKUP_COUNT: int = 10  # Mantener más logs en producción

    # DB Configuración
    DATABASE_URL: str = "sqlite:///labeling_app.db"
    DB_POOL_SIZE: int = 10  # Conexiones simultáneas
    DB_MAX_OVERFLOW: int = 20  # Conexiones adicionales con estrés
    DB_POOL_RECYCLE: int = 3600  # Reciclar conexiones cada hora
    DB_ECHO: bool = False  # SQL queries logging
    DB_CONNECT_TIMEOUT: int = 30  # segundos
    
    # Configuración de resiliencia
    MAX_REQUEST_SIZE: int = 100 * 1024 * 1024  # 100MB
    REQUEST_TIMEOUT: int = 60  # segundos
    MAX_RETRIES: int = 3  # Reintentos en errores transitivos
    RETRY_DELAY: float = 1.0  # segundos entre reintentos
    
    # Monitoreo y Health Checks
    HEALTH_CHECK_ENABLED: bool = True
    HEALTH_CHECK_INTERVAL: int = 60  # segundos
    DISK_SPACE_WARNING_THRESHOLD: int = 10 * 1024 * 1024 * 1024  # 10GB
    DB_CONNECTION_WARNING_THRESHOLD: float = 0.8  # 80% del pool
    
    # API Versioning
    API_VERSION: str = "v1"
    API_DEPRECATION_HEADERS: bool = True
    
    # Servicio externo - Notificaciones
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ADMIN_CHAT_ID: Optional[str] = None
    NOTIFICATION_RETRY_ATTEMPTS: int = 3

    @classmethod
    def from_env(cls):
        """Crear configuración desde variables de entorno con validación"""
        env = os.getenv('FLASK_ENV', 'development')
        
        config = cls(
            TRANSCRIPTION_PROJECTS_PATH=os.getenv('TRANSCRIPTION_PROJECTS_PATH', cls.TRANSCRIPTION_PROJECTS_PATH),
            AUDIO_FILES_PATH=os.getenv('AUDIO_FILES_PATH', cls.AUDIO_FILES_PATH),
            UPLOADS_PATH=os.getenv('UPLOADS_PATH', cls.UPLOADS_PATH),
            AUTOSAVE_INTERVAL=int(os.getenv('AUTOSAVE_INTERVAL', cls.AUTOSAVE_INTERVAL)),
            DEBUG=os.getenv('DEBUG', 'False' if env == 'production' else 'True').lower() == 'true',
            HOST=os.getenv('HOST', cls.HOST),
            PORT=int(os.getenv('PORT', cls.PORT)),
            WORKERS=int(os.getenv('WORKERS', cls.WORKERS if env == 'production' else 1)),
            WORKER_TIMEOUT=int(os.getenv('WORKER_TIMEOUT', cls.WORKER_TIMEOUT)),
            WORKER_CLASS=os.getenv('WORKER_CLASS', cls.WORKER_CLASS),
            JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY'),
            JWT_ACCESS_TOKEN_EXPIRES=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', cls.JWT_ACCESS_TOKEN_EXPIRES)),
            JWT_REFRESH_TOKEN_EXPIRES=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', cls.JWT_REFRESH_TOKEN_EXPIRES)),
            SECRET_KEY=os.getenv('SECRET_KEY'),
            FLASK_ENV=env,
            LOG_LEVEL=os.getenv('LOG_LEVEL', 'INFO' if env == 'production' else 'DEBUG').upper(),
            LOG_FORMAT=os.getenv('LOG_FORMAT', cls.LOG_FORMAT),
            LOG_FILE=os.getenv('LOG_FILE', cls.LOG_FILE),
            LOG_MAX_BYTES=int(os.getenv('LOG_MAX_BYTES', cls.LOG_MAX_BYTES)),
            LOG_BACKUP_COUNT=int(os.getenv('LOG_BACKUP_COUNT', cls.LOG_BACKUP_COUNT)),
            DATABASE_URL=os.getenv('DATABASE_URL', cls.DATABASE_URL),
            DB_POOL_SIZE=int(os.getenv('DB_POOL_SIZE', cls.DB_POOL_SIZE)),
            DB_MAX_OVERFLOW=int(os.getenv('DB_MAX_OVERFLOW', cls.DB_MAX_OVERFLOW)),
            DB_POOL_RECYCLE=int(os.getenv('DB_POOL_RECYCLE', cls.DB_POOL_RECYCLE)),
            DB_ECHO=os.getenv('DB_ECHO', 'False').lower() == 'true',
            DB_CONNECT_TIMEOUT=int(os.getenv('DB_CONNECT_TIMEOUT', cls.DB_CONNECT_TIMEOUT)),
            MAX_REQUEST_SIZE=int(os.getenv('MAX_REQUEST_SIZE', cls.MAX_REQUEST_SIZE)),
            REQUEST_TIMEOUT=int(os.getenv('REQUEST_TIMEOUT', cls.REQUEST_TIMEOUT)),
            MAX_RETRIES=int(os.getenv('MAX_RETRIES', cls.MAX_RETRIES)),
            RETRY_DELAY=float(os.getenv('RETRY_DELAY', cls.RETRY_DELAY)),
            HEALTH_CHECK_ENABLED=os.getenv('HEALTH_CHECK_ENABLED', 'True').lower() == 'true',
            HEALTH_CHECK_INTERVAL=int(os.getenv('HEALTH_CHECK_INTERVAL', cls.HEALTH_CHECK_INTERVAL)),
            DISK_SPACE_WARNING_THRESHOLD=int(os.getenv('DISK_SPACE_WARNING_THRESHOLD', cls.DISK_SPACE_WARNING_THRESHOLD)),
            DB_CONNECTION_WARNING_THRESHOLD=float(os.getenv('DB_CONNECTION_WARNING_THRESHOLD', cls.DB_CONNECTION_WARNING_THRESHOLD)),
            API_VERSION=os.getenv('API_VERSION', cls.API_VERSION),
            API_DEPRECATION_HEADERS=os.getenv('API_DEPRECATION_HEADERS', 'True').lower() == 'true',
            TELEGRAM_BOT_TOKEN=os.getenv('TELEGRAM_BOT_TOKEN'),
            TELEGRAM_ADMIN_CHAT_ID=os.getenv('TELEGRAM_ADMIN_CHAT_ID'),
            NOTIFICATION_RETRY_ATTEMPTS=int(os.getenv('NOTIFICATION_RETRY_ATTEMPTS', cls.NOTIFICATION_RETRY_ATTEMPTS))
        )
        
        # Validar configuración
        config.validate_production_config()
        return config
    
    def setup_logging(self):
        """Configura el sistema de logging"""
        from logging.handlers import RotatingFileHandler
        
        # Obtener el nivel de logging
        level = getattr(logging, self.LOG_LEVEL, logging.DEBUG)
        
        # Crear formateador
        formatter = logging.Formatter(self.LOG_FORMAT)
        
        # Configurar logger raíz
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Limpiar handlers existentes
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Handler para archivo con rotación
        try:
            file_handler = RotatingFileHandler(
                self.LOG_FILE,
                maxBytes=self.LOG_MAX_BYTES,
                backupCount=self.LOG_BACKUP_COUNT
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            logging.warning(f"No se pudo configurar el logging a archivo: {e}")
        
        # Configurar loggers específicos
        # Reducir verbosidad de loggers externos
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        logging.info(f"Sistema de logging configurado - Nivel: {self.LOG_LEVEL}")
        return root_logger

    def is_production(self):
        """Verifica si está en modo producción"""
        return self.FLASK_ENV == 'production'
    
    def validate_production_config(self):
        """Valida configuración crítica para producción"""
        if self.is_production():
            errors = []
            
            # Validar secretas
            if not self.JWT_SECRET_KEY:
                errors.append("JWT_SECRET_KEY es obligatorio en producción")
            elif len(self.JWT_SECRET_KEY) < 32:
                errors.append("JWT_SECRET_KEY debe tener al menos 32 caracteres (32+ aleatorios)")
            
            if not self.SECRET_KEY:
                errors.append("SECRET_KEY es obligatorio en producción")
            elif len(self.SECRET_KEY) < 32:
                errors.append("SECRET_KEY debe tener al menos 32 caracteres (32+ aleatorios)")
            
            # Validar base de datos
            if 'sqlite' in self.DATABASE_URL.lower():
                errors.append("SQLite NO es recomendado para producción. Usa PostgreSQL o MySQL")
            
            # Validar DEBUG
            if self.DEBUG:
                errors.append("DEBUG debe ser False en producción")
            
            # Validar workers
            if self.WORKERS < 2:
                errors.append(f"Se recomienda mínimo 2 workers en producción (actual: {self.WORKERS})")
            
            # Lanzar todos los errores
            if errors:
                raise ValueError(
                    "❌ CONFIGURACIÓN DE PRODUCCIÓN INVÁLIDA:\n" + 
                    "\n".join(f"  - {e}" for e in errors)
                )
            
            logging.info("✅ Validación de producción exitosa")
    
    def get_db_engine_config(self) -> dict:
        """Obtiene configuración para SQLAlchemy Engine"""
        config = {
            'echo': self.DB_ECHO,
            'pool_size': self.DB_POOL_SIZE,
            'max_overflow': self.DB_MAX_OVERFLOW,
            'pool_recycle': self.DB_POOL_RECYCLE,
            'pool_pre_ping': True,  # Verificar conexiones antes de usarlas
        }
        
        if 'postgresql' in self.DATABASE_URL.lower() or 'mysql' in self.DATABASE_URL.lower():
            config['connect_args'] = {'connect_timeout': self.DB_CONNECT_TIMEOUT}
        
        return config
    
    def get_gunicorn_config(self) -> dict:
        """Obtiene configuración recomendada para Gunicorn"""
        return {
            'bind': f'{self.HOST}:{self.PORT}',
            'workers': self.WORKERS,
            'worker_class': self.WORKER_CLASS,
            'worker_connections': 1000,
            'timeout': self.WORKER_TIMEOUT,
            'keepalive': 2,
            'max_requests': 1000,
            'max_requests_jitter': 50,
            'access_log_format': '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s',
        }
    
    def get_transcription_projects_path(self) -> str:
        """Obtiene la ruta absoluta a transcription_projects"""
        if os.path.isabs(self.TRANSCRIPTION_PROJECTS_PATH):
            return self.TRANSCRIPTION_PROJECTS_PATH
        else:
            # Ruta relativa al directorio de la aplicación
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            return os.path.join(app_root, self.TRANSCRIPTION_PROJECTS_PATH)
    
    def get_audio_files_path(self) -> str:
        """Obtiene la ruta absoluta a audio_files"""
        if os.path.isabs(self.AUDIO_FILES_PATH):
            return self.AUDIO_FILES_PATH
        else:
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            return os.path.join(app_root, self.AUDIO_FILES_PATH)
    
    def get_uploads_path(self) -> str:
        """Obtiene la ruta absoluta a uploads"""
        if os.path.isabs(self.UPLOADS_PATH):
            return self.UPLOADS_PATH
        else:
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            return os.path.join(app_root, self.UPLOADS_PATH)
    
    def ensure_directories_exist(self):
        """Crea directorios necesarios si no existen"""
        directories = [
            self.get_transcription_projects_path(),
            self.get_audio_files_path(),
            self.get_uploads_path(),
            os.path.dirname(self.LOG_FILE) if not os.path.isabs(self.LOG_FILE) else self.LOG_FILE
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                # Crear .gitkeep para que Git mantenga los directorios vacíos
                gitkeep = os.path.join(directory, '.gitkeep')
                if not os.path.exists(gitkeep):
                    with open(gitkeep, 'w') as f:
                        f.write("# Este archivo mantiene el directorio en Git\n")
            except Exception as e:
                logging.warning(f"No se pudo crear directorio {directory}: {e}")
    
    def get_summary(self) -> str:
        """Retorna resumen de configuración actual"""
        return f"""
╔════════════════════════════════════════════════════╗
║       CONFIGURACIÓN DE LA APLICACIÓN               ║
╚════════════════════════════════════════════════════╝
Ambiente:           {self.FLASK_ENV.upper()}
Debug:              {'ACTIVADO ⚠️' if self.DEBUG else 'Desactivado ✅'}
Servidor:           {self.HOST}:{self.PORT}
Workers:            {self.WORKERS}
Base de Datos:      {self.DATABASE_URL.split('://')[0].upper()}
Log Level:          {self.LOG_LEVEL}
API Version:        {self.API_VERSION}
Health Checks:      {'ACTIVADO' if self.HEALTH_CHECK_ENABLED else 'Desactivado'}

📁 RUTAS DE ARCHIVOS:
Transcription:      {self.get_transcription_projects_path()}
Audio Files:        {self.get_audio_files_path()}
Uploads:            {self.get_uploads_path()}
        """.strip()