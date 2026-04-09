"""
Configuración de Gunicorn para producción con máxima robustez
Úsalo: gunicorn -c gunicorn_config.py wsgi:app
"""
import os
import multiprocessing
import logging

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN RECOMENDADA PARA SERVIDOR REMOTO 24/7
# ═══════════════════════════════════════════════════════════════════

# Entorno
env = os.getenv('FLASK_ENV', 'production')

# ─────────────────────────────────────────────────────────────────
# NETWORKING
# ─────────────────────────────────────────────────────────────────
bind = [
    os.getenv('HOST', '0.0.0.0') + ':' + os.getenv('PORT', '8080'),
]
backlog = 2048  # Cola de conexiones pendientes

# ─────────────────────────────────────────────────────────────────
# WORKERS Y CONCURRENCIA  
# ─────────────────────────────────────────────────────────────────
# Workers = (2 × CPU_cores) + 1
workers = int(os.getenv('WORKERS', (multiprocessing.cpu_count() * 2) + 1))
worker_class = os.getenv('WORKER_CLASS', 'sync')  # 'sync', 'gevent', 'async'
worker_connections = 1000  # Máx conexiones por worker
max_requests = 1000  # Reinicia worker después de N requests (previene memory leaks)
max_requests_jitter = 50  # Variación para evitar reinicio simultáneo
timeout = int(os.getenv('WORKER_TIMEOUT', 120))  # timeout por request
keepalive = 2  # Segundos para mantener conexión HTTP alive

# ─────────────────────────────────────────────────────────────────
# DEBUGGING Y LOGGING
# ─────────────────────────────────────────────────────────────────
debug = False  # NUNCA True en producción
loglevel = os.getenv('LOG_LEVEL', 'info')  # debug, info, warning, error, critical
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" '
    'response_time=%(D)sμs'
)
errorlog = os.getenv('ERROR_LOG', 'logs/gunicorn_error.log')
accesslog = os.getenv('ACCESS_LOG', 'logs/gunicorn_access.log')
capture_output = True  # Capturar stdout/stderr

# ─────────────────────────────────────────────────────────────────
# PROCESOS Y RECURSOS
# ─────────────────────────────────────────────────────────────────
daemon = False  # Systemd/supervisor lo maneja
pidfile = None  # Systemd/supervisor lo maneja
umask = 0o022
user = None  # Especificar usuario si lo necesitas
group = None

# ─────────────────────────────────────────────────────────────────
# HOOKS DE CICLO DE VIDA
# ─────────────────────────────────────────────────────────────────
def on_starting(server):
    """Ejecutado cuando Gunicorn está a punto de arrancar"""
    logging.info("🟢 Gunicorn iniciando...")

def when_ready(server):
    """Ejecutado cuando el servidor está listo para aceptar requests"""
    logging.info("✅ Gunicorn LISTO para recibir requests")
    logging.info(f"   Workers: {workers}")
    logging.info(f"   Bind: {bind}")
    logging.info(f"   Environment: {env}")

def on_exit(server):
    """Ejecutado cuando Gunicorn se apaga"""
    logging.info("🏁 Gunicorn apagándose...")

def post_worker_init(worker):
    """Ejecutado después de que cada worker se inicia"""
    logging.info(f"🚀 Worker {worker.pid} iniciado")

def worker_int(worker):
    """Manejador de SIGINT para workers"""
    logging.info(f"🛑 Worker {worker.pid} recibió SIGINT")

def worker_abort(worker):
    """Ejecutado cuando un worker fue abortado"""
    logging.warning(f"⚠️ Worker {worker.pid} fue abortado")

# ─────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE SEGURIDAD
# ─────────────────────────────────────────────────────────────────
secure_scheme_headers = {
    'X-FORWARDED_PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on',
}
forwarded_allow_ips = os.getenv('FORWARDED_ALLOW_IPS', '*')  # Ajustar según proxy
raw_env = [
    'FLASK_ENV=production',
    f'LOG_LEVEL={os.getenv("LOG_LEVEL", "INFO")}',
]

# ─────────────────────────────────────────────────────────────────
# INSTRUCCIONES DE USO
# ─────────────────────────────────────────────────────────────────
"""
INSTALACIÓN:
    pip install gunicorn

INICIO EN PRODUCCIÓN:
    # Directamente
    gunicorn -c gunicorn_config.py wsgi:app

    # Con systemd (RECOMENDADO)
    [Unit]
    Description=Labeling App
    After=network.target
    
    [Service]
    User=www-data
    WorkingDirectory=/path/to/Labeling_app/src
    ExecStart=/path/to/venv/bin/gunicorn -c gunicorn_config.py wsgi:app
    Restart=always
    RestartSec=10
    StandardOutput=journal
    StandardError=journal
    
    [Install]
    WantedBy=multi-user.target

    # Activar: sudo systemctl enable --now labeling-app
    # Ver logs: journalctl -u labeling-app -f

MONITOREO:
    # Ver workers
    ps aux | grep gunicorn
    
    # Ver puertos
    netstat -tlnp | grep gunicorn
    
    # Ver recursos
    top -p $(pidof gunicorn)

GRACEFUL RELOAD (sin downtime):
    kill -HUP $(cat gunicorn.pid)

GRACEFUL SHUTDOWN:
    kill -TERM $(cat gunicorn.pid)
    # Espera 30 segundos a completar requests, luego force-kills
"""
