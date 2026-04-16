FROM python:3.10-slim

WORKDIR /app

# Instala dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc libsqlite3-dev libpq-dev postgresql-client \
    curl git && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Crear directorios necesarios
RUN mkdir -p /app/logs /app/data/backups

# Copiar requirements
COPY src/requirements/requirements.txt /app/requirements.txt

# Actualizar pip e instalar paquetes
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt gunicorn && \
    rm -rf /root/.cache

# Copiar código de la aplicación
COPY src /app/src
COPY docker/web_app/gunicorn_config.py /app/gunicorn_config.py

# Cambiar a directorio de app
WORKDIR /app/src

# Puerto expuesto
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/login || exit 1

# Comando para arrancar Gunicorn
CMD ["gunicorn", \
     "--config", "/app/gunicorn_config.py", \
     "--bind", "0.0.0.0:3000", \
     "--workers", "4", \
     "--worker-class", "sync", \
     "--timeout", "60", \
     "--access-logfile", "/app/logs/access.log", \
     "--error-logfile", "/app/logs/error.log", \
     "--log-level", "info", \
     "app:app"]
