# 🚀 Guía de Deployment a Producción (24/7)

> **Estado Crítico:** Este documento te guiará para deployar la plataforma de anotación con robustez para producción.

---

## ⚠️ Pre-requisitos Críticos

```bash
✅ Docker & Docker Compose instalado
✅ PostgreSQL 15+ (o Docker)
✅ SSL/TLS Certificate (Let's Encrypt recomendado)
✅ Servidor remoto con mínimo 2 CPU cores, 4GB RAM
✅ Almacenamiento SSD para base de datos (mínimo 50GB)
```

---

## 📋 Fase 1: Configuración Básica (1-2 horas)

### 1.1 Generar Secretas Seguras

```bash
# Generar JWT_SECRET_KEY (32+ caracteres)
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generar SECRET_KEY para sesiones
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generar contraseña PostgreSQL fuerte
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))"
```

### 1.2 Configurar Variables de Entorno

**Archivo: `envs/postgres.env`**
```bash
POSTGRES_USER=labeling_user
POSTGRES_PASSWORD=your_strong_password_here
POSTGRES_DB=labeling_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin_password_here
```

**Archivo: `envs/web_app.env`**
```bash
# Base de Datos
DATABASE_URL=postgresql://labeling_user:your_password@postgres:5432/labeling_db

# Seguridad
JWT_SECRET_KEY=your_generated_key_here
SECRET_KEY=your_generated_key_here

# Servidor
FLASK_ENV=production
HOST=0.0.0.0
PORT=8080
WORKERS=4
DEBUG=False

# Logging
LOG_LEVEL=INFO

# Backups
BACKUP_DIR=data/backups
MAX_BACKUPS=30
```

### 1.3 Crear Estructura de Directorios

```bash
mkdir -p data/backups
mkdir -p data/transcription_projects
mkdir -p logs
chmod 755 data/backups logs
```

---

## 📦 Fase 2: Migración de Base de Datos (30-45 minutos)

### 2.1 Si Vienes desde SQLite

```bash
# 1. Asegúrate de que SQLite está en ./src/labeling_app.db
ls -lh src/labeling_app.db

# 2. Inicia PostgreSQL con Docker
docker-compose up -d postgres

# 3. Espera a que PostgreSQL esté lista
sleep 10 && docker logs db | grep "database system is ready"

# 4. Instala dependencias necesarias
pip install -r src/requirements/requirements.txt

# 5. Ejecuta script de migración
cd src && python scripts/migrate_to_postgresql.py

# 6. Verifica la migración
docker exec -it db psql -U labeling_user -d labeling_db -c "SELECT COUNT(*) FROM segments;"
```

### 2.2 Si Es Nueva Instalación

```bash
# 1. Inicia los servicios
docker-compose up -d

# 2. Espera a initialization
sleep 15

# 3. Verifica que las tablas existen
docker exec -it db psql -U labeling_user -d labeling_db -c "\dt"
```

---

## 🔐 Fase 3: Seguridad (2-3 horas)

### 3.1 HTTPS/SSL Configuration

#### Opción A: Let's Encrypt (Recomendado)

```bash
# 1. Instala Certbot
sudo apt-get install certbot python3-certbot-nginx

# 2. Obtén certificado (reemplaza domain.com)
sudo certbot certonly --standalone \
  -d transcriptions.domain.com \
  -d www.transcriptions.domain.com \
  --agree-tos \
  -m admin@domain.com

# 3. Rutas de certificado:
# - Private Key: /etc/letsencrypt/live/transcriptions.domain.com/privkey.pem
# - Certificate: /etc/letsencrypt/live/transcriptions.domain.com/fullchain.pem
```

#### Opción B: Self-Signed (Desarrollo)

```bash
# Generar certificado auto-firmado
openssl req -x509 -newkey rsa:4096 \
  -keyout certs/key.pem \
  -out certs/cert.pem \
  -days 365 -nodes \
  -subj "/C=CL/O=NuestraMemoria/CN=transcriptions.local"

mkdir -p certs
chmod 600 certs/*.pem
```

### 3.2 Nginx Reverse Proxy

**Archivo: `docker/nginx/Dockerfile`**
```dockerfile
FROM nginx:1.25-alpine

RUN mkdir -p /etc/nginx/conf.d

COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80 443
```

**Archivo: `docker/nginx/nginx.conf`**
```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript;

    include /etc/nginx/conf.d/*.conf;
}
```

**Archivo: `docker/nginx/default.conf`**
```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name transcriptions.domain.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name transcriptions.domain.com;

    ssl_certificate /etc/letsencrypt/live/transcriptions.domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/transcriptions.domain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy al backend
    location / {
        proxy_pass http://web_app:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # Limitar uploads
    client_max_body_size 100M;
}
```

### 3.3 Actualizar docker-compose.yml

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:1.25-alpine
    container_name: nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro  # Certificados SSL
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - web_app
    networks:
      - app_network

  web_app:
    # ... existing config ...
    networks:
      - app_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    # ... existing config ...
    networks:
      - app_network

networks:
  app_network:
    driver: bridge
```

---

## 🔄 Fase 4: Backups Automáticos (20 minutos)

### 4.1 Configurar Cron para Backups Horarios

```bash
# Ejecutar setup de backups
bash scripts/setup_backups.sh

# Verificar que fue agregado a crontab
crontab -l | grep backup_service

# Ver logs de backups
tail -f data/backups/cron.log
```

### 4.2 Backup Manual

```bash
# Hacer backup manual
cd src && python services/backup_service.py

# Listar todos los backups
python services/backup_service.py list
```

---

## 📊 Fase 5: Monitoreo y Alertas (1 hora)

### 5.1 Health Check Endpoint

```bash
# Endpoint de salud (nuevo)
curl http://localhost:8080/api/v2/transcriptions/health

# Respuesta:
{
  "status": "healthy",
  "database": {"status": "healthy", "response_time_ms": 2.5},
  "disk": {"free_gb": 45.2, "percent_used": 35},
  "memory": {"percent_used": 42},
  "cpu": {"percent": 25}
}
```

### 5.2 Configurar Alertas Telegram (OPT)

```bash
# En web_app.env:
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_CHAT_ID=your_chat_id_here

# El sistema enviará alertas si:
# - DB response > 5s
# - Disco < 10GB
# - Memoria > 85%
# - Múltiples workers mueren
```

---

## ✅ Fase 6: Testing (2-3 horas)

### 6.1 Verificar Funcionalidad

```bash
# 1. Login test
curl -X POST http://localhost/api/v2/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 2. Rate limiting test (debe fallar en el 6to intento)
for i in {1..10}; do
  curl -X POST http://localhost/api/v2/login \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "wrong"}' \
    echo "Intento $i"
  sleep 1
done

# 3. Load test (100 usuarios simultáneos)
ab -n 100 -c 100 -H "Authorization: Bearer $JWT_TOKEN" \
  http://localhost/api/v2/transcriptions/projects
```

### 6.2 Verificar Backups

```bash
# Listar archivos recientes
ls -lrh data/backups/

# Restaurar desde backup (prueba)
docker exec -it db pg_restore -U labeling_user -d labeling_db_test backup.dump
```

### 6.3 Verificar Seguridad SSL

```bash
# Probar certificado SSL
openssl s_client -connect transcriptions.domain.com:443 -showcerts

# Probar con curl
curl -I https://transcriptions.domain.com
```

---

## 🚨 Monitoreo Continuo (24/7)

### Logs a Revisar Diariamente

```bash
# Logs de aplicación
docker logs -f web_app

# Logs de nginx
docker logs -f nginx

# Logs de PostgreSQL
docker logs -f postgres

# Logs de backups
tail -f data/backups/cron.log
```

### Métricas Críticas

| Métrica | Alerta | Crít |
|---------|--------|------|
| DB Response Time | > 5s | > 10s |
| Disco Libre | < 10GB | < 5GB |
| Memoria | > 80% | > 95% |
| CPU | > 70% | > 90% |
| Failed Requests | > 1% | > 5% |

---

## 🔧 Troubleshooting

### PostgreSQL no inicia
```bash
docker-compose logs postgres
# Verificar permisos
docker exec postgres chown -R postgres:postgres /var/lib/postgresql/data
```

### Rate Limiting bloqueando usuarios legítimos
```bash
# Reducir límites en config.py
DB_POOL_SIZE = 20
WORKERS = 8

# O verificar si es atacante
curl -H "X-Forwarded-For: <ip>" http://localhost/api/v2/login
```

### Backups no se crean
```bash
# Verificar conexión PostgreSQL
pg_isready -h localhost -p 6543 -U labeling_user

# Crear backup manual
python src/services/backup_service.py

# Ver logs
cat data/backups/cron.log
```

---

## 📞 Soporte

Para issues específicos:
1. Revisar `/logs/app.log`
2. Ejecutar health check endpoint
3. Verificar `docker-compose logs`
4. Consultar con equipo de DevOps

---

**Última actualización:** Abril 2026
**Versión:** 1.0.0 (Production Ready)
