FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias del sistema requeridas por psycopg2, librosa/soundfile y healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-dev \
    libpq-dev \
    postgresql-client \
    curl \
    libsndfile1 \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Directorios necesarios para logs y datos persistentes
RUN mkdir -p /app/logs /app/src/logs /app/data/backups /app/data/transcription_projects

# Dependencias Python
COPY src/requirements/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirements.txt

# Código de aplicación
COPY src /app/src

WORKDIR /app/src

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/login || exit 1

# Usa la app WSGI (wsgi.py) con configuración de Gunicorn versionada en src/
CMD ["gunicorn", "--config", "/app/src/gunicorn.conf.py", "wsgi:app"]
