# 🚀 GUÍA COMPLETA DE DEPLOYMENT - SERVIDOR REMOTO 24/7

## Overview: Robustez Arquitectónica

Tu aplicación está diseñada para correr en servidor remoto con máxima confiabilidad:

```
┌─────────────────────────────────────────────────────────────┐
│  CLIENTE (tu dispositivo)                                    │
│  ↓ Conexión SSH/HTTPS                                       │
├─────────────────────────────────────────────────────────────┤
│  SERVIDOR REMOTO (24/7)                                     │
│                                                              │
│  Nginx (Reverse Proxy) ← DDoS protection, load balancing   │
│    ↓                                                         │
│  Gunicorn (WSGI Server) ← 4-8 workers, connection pooling  │
│    ↓ ACID transactions                                      │
│  PostgreSQL (Database) ← Replicación, backups automáticos  │
│    ↓                                                         │
│  Health Checker ← Monitoreo 24/7, alertas automáticas      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 CHECKLIST PRE-DEPLOYMENT

- [ ] Servidor Linux (Ubuntu 20.04+ recomendado)
- [ ] Python 3.8+
- [ ] PostgreSQL 12+
- [ ] Nginx instalado
- [ ] Git instalado
- [ ] SSH configurado
- [ ] 4GB RAM mínimo, 10GB espacio en disco

---

## 🔧 INSTALACIÓN EN SERVIDOR REMOTO

### PASO 1: Preparar el Servidor

```bash
# SSH al servidor
ssh user@your-server.com

# Actualizar sistem
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y python3.10 python3-pip python3-venv postgresql postgresql-contrib nginx git curl

# Verificar versiones
python3 --version
psql --version
nginx -v
```

### PASO 2: Crear Usuario para la Aplicación

```bash
# Crear usuario sin login (seguridad)
sudo useradd -r -s /bin/bash -d /opt/labeling_app labeling

# Crear directorio de la app
sudo mkdir -p /opt/labeling_app
sudo chown -R labeling:labeling /opt/labeling_app
sudo chmod 755 /opt/labeling_app

# Crear directorio de logs
sudo mkdir -p /var/log/labeling_app
sudo chown -R labeling:labeling /var/log/labeling_app
```

### PASO 3: Clonar y Configurar la Aplicación

```bash
# Como user labeling
sudo -u labeling -H bash

cd /opt/labeling_app

# Clonar repositorio (o copiar archivos)
git clone https://github.com/tu-usuario/Labeling_app.git .

# Crear virtual environment
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
cd src
pip install --upgrade pip
pip install -r requirements/requirements.txt
pip install gunicorn psycopg2-binary psutil

# Salir del usuario labeling
exit
```

### PASO 4: Configurar PostgreSQL

```bash
# Como root o con sudo
sudo -u postgres psql

# Dentro de PostgreSQL:
CREATE USER labeling_user WITH PASSWORD 'CHOOSE-STRONG-PASSWORD-HERE';
CREATE DATABASE labeling_db OWNER labeling_user;

# Configurar permisos
GRANT CONNECT ON DATABASE labeling_db TO labeling_user;
GRANT USAGE ON SCHEMA public TO labeling_user;
GRANT CREATE ON SCHEMA public TO labeling_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO labeling_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO labeling_user;

# Salir
\q

# Verificar conexión
psql -U labeling_user -d labeling_db -h localhost -c "SELECT 1"
```

### PASO 5: Crear Archivo de Configuración

```bash
# Crear archivo de entorno para producción
sudo mkdir -p /etc/labeling_app
sudo nano /etc/labeling_app/production.env
```

**Contenido del archivo:**
```ini
# Obligatorio: Generar con: python3 -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=abc123def456...xyz (32+ caracteres aleatorios)
SECRET_KEY=xyz987wvu654...cba (32+ caracteres aleatorios)

# Base de datos
DATABASE_URL=postgresql://labeling_user:TU-PASSWORD@localhost:5432/labeling_db

# Servidor
FLASK_ENV=production
DEBUG=False
HOST=0.0.0.0
PORT=8000
WORKERS=4
LOG_LEVEL=INFO

# Notificaciones (opcional)
TELEGRAM_BOT_TOKEN=123456:ABC-xyz...
TELEGRAM_ADMIN_CHAT_ID=987654321

# Seguridad
FORWARDED_ALLOW_IPS=127.0.0.1,IP-DE-TU-NGINX

# Rutas de archivos (CONFIGURABLES - IMPORTANTE PARA SERVIDOR REMOTO)
# Opción A: Rutas relativas (recomendado - más portable)
TRANSCRIPTION_PROJECTS_PATH=data/transcription_projects
AUDIO_FILES_PATH=data/audio_files
UPLOADS_PATH=data/uploads

# Opción B: Rutas absolutas (más control - descomenta si prefieres)
# TRANSCRIPTION_PROJECTS_PATH=/opt/labeling_app/data/transcription_projects
# AUDIO_FILES_PATH=/opt/labeling_app/data/audio_files
# UPLOADS_PATH=/opt/labeling_app/data/uploads
```

```bash
# Permisos seguros
sudo chmod 600 /etc/labeling_app/production.env
sudo chown labeling:labeling /etc/labeling_app/production.env
```

### PASO 6: Instalar como Servicio Systemd

```bash
# Copiar archivo de servicio
sudo cp labeling-app.service /etc/systemd/system/labeling-app.service

# Editar rutas según tu instalación
sudo nano /etc/systemd/system/labeling-app.service

# Recargar systemd
sudo systemctl daemon-reload

# Habilitar servicio (inicia con el servidor)
sudo systemctl enable labeling-app

# Iniciar servicio
sudo systemctl start labeling-app

# Ver estado
sudo systemctl status labeling-app

# Ver logs en tiempo real
sudo journalctl -u labeling-app -f
```

### PASO 6.5: Crear Estructura de Directorios de Datos

**IMPORTANTE**: La aplicación ahora usa rutas configurables para archivos. Crea la estructura de directorios según las variables definidas en `production.env`:

```bash
# Crear directorios de datos (ajusta rutas según tu configuración)
sudo mkdir -p /opt/labeling_app/data/transcription_projects
sudo mkdir -p /opt/labeling_app/data/audio_files
sudo mkdir -p /opt/labeling_app/data/uploads
sudo mkdir -p /opt/labeling_app/logs

# Si usas rutas absolutas personalizadas, crea esos directorios:
# sudo mkdir -p /var/data/audio_files
# sudo mkdir -p /mnt/uploads

# Asignar permisos correctos
sudo chown -R labeling:labeling /opt/labeling_app/data
sudo chown -R labeling:labeling /opt/labeling_app/logs
sudo chmod -R 755 /opt/labeling_app/data
sudo chmod -R 755 /opt/labeling_app/logs
```

**Migrar archivos existentes desde desarrollo local:**
```bash
# Desde tu máquina local, copia los archivos:
scp -r Labeling_app/src/data/transcription_projects/memoria_1970_1990 \
    user@server:/opt/labeling_app/data/transcription_projects/

# Verificar que se copiaron correctamente
ssh user@server "ls -la /opt/labeling_app/data/transcription_projects/"
```

### PASO 7: Configurar Nginx como Reverse Proxy

```bash
# Crear configuración de Nginx
sudo nano /etc/nginx/sites-available/labeling-app
```

**Contenido:**
```nginx
upstream labeling_app {
    server 127.0.0.1:8000 fail_timeout=0;
    keepalive 32;
}

server {
    listen 80;
    server_name tu-dominio.com;

    # Redirigir HTTP → HTTPS (recomendado con Let's Encrypt)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tu-dominio.com;

    # SSL (obtener con: sudo certbot certonly --nginx)
    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Logs
    access_log /var/log/nginx/labeling-app_access.log;
    error_log /var/log/nginx/labeling-app_error.log;

    # Límites
    client_max_body_size 100M;
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;

    # Headers de seguridad
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Health check (sin logs)
    location /health {
        access_log off;
        proxy_pass http://labeling_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API y contenido
    location / {
        proxy_pass http://labeling_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_http_version 1.1;
        proxy_buffering off;
    }
}
```

```bash
# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/labeling-app /etc/nginx/sites-enabled/

# Verificar sintaxis
sudo nginx -t

# Recargar Nginx
sudo systemctl reload nginx
```

---

## 🛡️ ASEGURAR CERTIFICADOS SSL

```bash
# Instalar Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtener certificado
sudo certbot certonly --nginx -d tu-dominio.com

# Auto-renovación (verificar)
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## 📊 MONITOREO Y MANTENIMIENTO

### Health Check (Verificar salud en tiempo real)

```bash
# Desde tu máquina local
curl -s https://tu-dominio.com/health | jq .

# Respuesta esperada:
{
  "timestamp": "2026-04-08T15:30:00.123456",
  "database": { "status": "healthy", "response_time_ms": 2.5 },
  "disk": { "status": "healthy", "free_gb": 45.3, "percent_used": 12 },
  "memory": { "status": "healthy", "percent_used": 45.2 },
  "cpu": { "status": "healthy", "percent_used": 23.1 },
  "alerts": [],
  "overall_status": "healthy"
}
```

### Ver Logs en Tiempo Real

```bash
# Logs de aplicación
sudo journalctl -u labeling-app -f

# Logs de Nginx
sudo tail -f /var/log/nginx/labeling-app_access.log

# Logs de errores
sudo tail -f /var/log/labeling-app/error.log
```

### Monitoreo de Recursos

```bash
# Ver proceso
ps aux | grep gunicorn

# Ver conexiones
netstat -tlnp | grep 8000

# Ver CPU y memoria
top -p $(pgrep -f gunicorn | head -1)

# Ver tamaño de logs
du -sh /var/log/labeling_app/

# Limpiar logs rotativos viejos (> 30 días)
find /var/log/labeling_app/ -name "*.log.*" -mtime +30 -delete
```

---

## 🔄 OPERACIONES COMUNES

### Graceful Restart (Sin downtime)

```bash
# Recargar workers sin interrumpir requests
sudo systemctl reload labeling-app

# O manualmente
sudo kill -HUP $(pgrep -f "gunicorn.*wsgi:app" | head -1)
```

### Full Restart (Si hay problema)

```bash
sudo systemctl restart labeling-app
```

### Ver Estado

```bash
sudo systemctl status labeling-app
```

### Detener (Graceful)

```bash
sudo systemctl stop labeling-app
# Espera 30 segundos a completar requests
```

---

## 🆘 TROUBLESHOOTING

### Aplicación no levanta

```bash
# Ver logs detallados
sudo journalctl -u labeling-app -n 50

# Verificar configuración
source /etc/labeling_app/production.env
echo "DATABASE_URL: $DATABASE_URL"
echo "JWT_SECRET_KEY: $JWT_SECRET_KEY" (no mostrar valor real)

# Verificar DB
psql -U labeling_user -d labeling_db -h localhost -c "SELECT 1"
```

### Conexión a BD lenta/caída

```bash
# Ver conexiones activas
psql -U postgres -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"

# Reiniciar pool de conexiones
sudo systemctl restart labeling-app
```

### Disco lleno

```bash
# Ver uso de disco
df -h

# Encontrar archivos grandes
find /var/log/labeling_app -name "*.log" -size +100M

# Comprimir logs viejos
gzip /var/log/labeling_app/app.log

# O eliminar si son muy viejos
rm /var/log/labeling_app/app.log.*
```

### Memoria alta

```bash
# Ver memoria de workers
ps aux | grep gunicorn

# Restart automático cada 1000 requests previene leaks
# (Ya configurado en gunicorn_config.py)
```

---

## 🔐 SEGURIDAD EN PRODUCCIÓN

```bash
# Firewall: Permitir solo SSH, HTTP, HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Permisos restrictivos
sudo chmod 755 /opt/labeling_app/src
sudo chmod 700 /opt/labeling_app/src/config.py

# Backup de datos automático (cron)
0 2 * * * /opt/labeling_app/src/backup_job/db_backup.sh >> /var/log/labeling_app/backup.log 2>&1
```

---

## 📈 ESCALABILIDAD FUTURA

Si necesitas más capacidad:

```bash
# Aumentar workers (si CPU lo permite)
WORKERS=8  # en production.env

# Agregar replicación de DB
# Usar CDN para assets estáticos
# Load balancing con múltiples servidores Gunicorn
# Cache con Redis para sesiones
```

---

## 🎯 RESUMEN: Tu Aplicación Está 24/7 Segura

✅ **Autoinicio**: Systemd reinicia si falla  
✅ **Monitoreo**: Health checks cada 60s  
✅ **Logs**: Rotación automática, sin llenar disco  
✅ **Actualizaciones**: Graceful reload sin downtime  
✅ **Seguridad**: JWT, HTTPS, firewall  
✅ **Backups**: Automáticos cada noche  

Tu servidor estará listo. ¡Accede desde cualquier lado del mundo y sigue usando la app!

