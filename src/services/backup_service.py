#!/usr/bin/env python3
"""
Servicio de backup automático para bases de datos
Soporta PostgreSQL y SQLite
Ambiente: desarrollo (local) o producción (S3)
"""
import os
import logging
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Agregar src directory al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupService:
    """Servicio para hacer backups automáticos de la base de datos"""
    
    def __init__(self, config):
        self.config = config
        self.backup_dir = Path(config.get('BACKUP_DIR', 'data/backups'))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = config.get('MAX_BACKUPS', 30)  # Retener últimos 30 días
        
        self.db_url = config.get('DATABASE_URL', 'sqlite:///labeling_app.db')
        logger.info(f"BackupService inicializado - Directorio: {self.backup_dir}")
    
    def backup_postgresql(self):
        """Backup de base de datos PostgreSQL"""
        logger.info("🔄 Iniciando backup de PostgreSQL...")
        
        try:
            # Parsear DATABASE_URL: postgresql://user:password@host:port/db
            # Formato: postgresql://labeling_user:password@postgres:5432/labeling_db
            db_url = self.db_url
            
            # Extraer componentes
            if '://' not in db_url:
                logger.error("❌ DATABASE_URL inválida")
                return False
            
            # Remover el prefijo postgresql://
            auth_and_host = db_url.split('://')[1]
            
            if '@' not in auth_and_host:
                logger.error("❌ DATABASE_URL debe contener credentials")
                return False
            
            auth, host_db = auth_and_host.split('@')
            user, password = auth.split(':') if ':' in auth else (auth, '')
            
            if ':' in host_db:
                host_port, db_name = host_db.rsplit('/', 1)
                host, port = host_port.rsplit(':', 1)
            else:
                host = host_db.rsplit('/', 1)[0]
                port = '5432'
                db_name = host_db.rsplit('/', 1)[1] if '/' in host_db else 'labeling_db'
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f"backup_postgres_{timestamp}.sql.gz"
            
            # pg_dump
            cmd = [
                'pg_dump',
                '--host', host,
                '--port', port,
                '--username', user,
                '--no-password',
                '--format=plain',
                db_name
            ]
            
            # Usar password si está disponible
            env = os.environ.copy()
            if password:
                env['PGPASSWORD'] = password
            
            logger.info(f"   Ejecutando: pg_dump de {db_name}@{host}")
            
            # Hacer dump y comprimir
            with open(backup_file, 'wb') as f_out:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    timeout=300
                )
                
                if result.returncode != 0:
                    logger.error(f"❌ pg_dump failed: {result.stderr.decode()}")
                    return False
                
                # Comprimir
                with gzip.GzipFile(fileobj=f_out, mode='wb') as f_gz:
                    f_gz.write(result.stdout)
            
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Backup creado: {backup_file.name} ({size_mb:.2f} MB)")
            
            # Limpiar backups antiguos
            self._cleanup_old_backups()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en backup PostgreSQL: {e}")
            return False
    
    def backup_sqlite(self):
        """Backup de base de datos SQLite"""
        logger.info("🔄 Iniciando backup de SQLite...")
        
        try:
            # Extraer ruta del archivo SQLite
            # Formato: sqlite:///path/to/db.db o sqlite:////absolute/path/db.db
            db_path = self.db_url.replace('sqlite:///', '')
            
            if not os.path.exists(db_path):
                logger.error(f"❌ Archivo SQLite no encontrado: {db_path}")
                return False
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f"backup_sqlite_{timestamp}.db.gz"
            
            logger.info(f"   Copiando {db_path}...")
            
            # Copiar con compresión
            with open(db_path, 'rb') as f_in:
                with gzip.open(backup_file, 'wb') as f_gz:
                    shutil.copyfileobj(f_in, f_gz)
            
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Backup creado: {backup_file.name} ({size_mb:.2f} MB)")
            
            # Limpiar backups antiguos
            self._cleanup_old_backups()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en backup SQLite: {e}")
            return False
    
    def backup(self):
        """Realiza backup según el tipo de base de datos"""
        if 'postgresql' in self.db_url.lower():
            return self.backup_postgresql()
        elif 'sqlite' in self.db_url.lower():
            return self.backup_sqlite()
        else:
            logger.error(f"❌ Tipo de DB no soportado: {self.db_url}")
            return False
    
    def _cleanup_old_backups(self):
        """Elimina backups más antiguos que max_backups"""
        try:
            backups = sorted(
                self.backup_dir.glob('backup_*'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            if len(backups) > self.max_backups:
                for old_backup in backups[self.max_backups:]:
                    logger.info(f"   🗑️  Eliminando backup antiguo: {old_backup.name}")
                    old_backup.unlink()
        
        except Exception as e:
            logger.warning(f"⚠️  Error limpiando backups antiguos: {e}")
    
    def list_backups(self):
        """Lista todos los backups disponibles"""
        backups = sorted(
            self.backup_dir.glob('backup_*'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        logger.info(f"📋 Backups disponibles ({len(backups)}):")
        for backup in backups[:10]:  # Mostrar últimos 10
            size_mb = backup.stat().st_size / (1024 * 1024)
            date = datetime.fromtimestamp(backup.stat().st_mtime)
            logger.info(f"   {backup.name} ({size_mb:.2f} MB) - {date}")


def main():
    """Función principal para ejecutar como script"""
    
    # Cargar config
    from config import Config
    config = Config.from_env()
    
    backup_config = {
        'DATABASE_URL': config.DATABASE_URL,
        'BACKUP_DIR': os.getenv('BACKUP_DIR', 'data/backups'),
        'MAX_BACKUPS': int(os.getenv('MAX_BACKUPS', 30))
    }
    
    service = BackupService(backup_config)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        service.list_backups()
    else:
        success = service.backup()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
