FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Instala dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libsqlite3-dev \
    libpq-dev \
    postgresql-client \
    curl \
    git \
    ffmpeg \
    libsndfile1 \
    ca-certificates \
    tini && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Crear directorios necesarios
RUN mkdir -p /app/logs /app/data/backups && \
    useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Copiar requirements
COPY src/requirements/requirements.txt /app/requirements.txt

# Actualizar pip e instalar paquetes
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt gunicorn && \
    rm -rf /root/.cache

# Copiar código de la aplicación
COPY src /app/src
COPY src/gunicorn_config.py /app/gunicorn_config.py

# Cambiar a directorio de app
WORKDIR /app/src

USER appuser

# Puerto expuesto
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]

# Comando para arrancar Gunicorn
CMD ["gunicorn", \
     "--config", "/app/gunicorn_config.py", \
     "wsgi:app"]
