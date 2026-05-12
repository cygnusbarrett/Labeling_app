# 🚀 DEPLOYMENT GUIDE - PRODUCTION SETUP

## 📋 Descripción

Este proyecto está configurado para deployarse en producción con:
- ✅ **Nginx** - Reverse proxy con SSL/TLS
- ✅ **Flask** - Servidor de aplicación
- ✅ **PostgreSQL** - Base de datos persistente
- ✅ **Redis** - Cache y sesiones distribuidas
- ✅ **Docker Compose** - Orquestación de contenedores
- ✅ **SSL/TLS** - HTTPS seguro
- ✅ **Load Balancing** - Nginx como load balancer
- ✅ **Rate Limiting** - Protección contra ataques
- ✅ **Health Checks** - Monitoreo de servicios

---

## 🔧 **SETUP LOCAL (Simular Producción)**

### 1. Clonar el repositorio

```bash
cd ~/tu-ruta
git clone <tu-repo>
cd Labeling_app
```

### 2. Preparar variables de entorno

```bash
# Copiar el archivo real de producción
cp envs/production.env.example envs/production.env

# Restringir permisos del archivo de secretos
chmod 600 envs/production.env

# Editar con tus valores seguros
nano envs/production.env
```

**Campos críticos a cambiar:**
```env
DB_USER=labeling_user
DB_PASSWORD=cambiar_esto_por_valor_seguro
DB_NAME=labeling_db
REDIS_PASSWORD=cambiar_esto_por_valor_seguro
DATABASE_URL=postgresql://labeling_user:cambiar_esto_por_valor_seguro@postgres:5432/labeling_db
REDIS_URL=redis://:cambiar_esto_por_valor_seguro@redis:6379
JWT_SECRET_KEY=cambiar_esto_por_valor_seguro_de_128_caracteres
SECRET_KEY=cambiar_esto_por_valor_seguro_de_128_caracteres
```

### 3. Generar secretos seguros

```bash
# JWT Secret (128 caracteres)
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(64))"

# Secret Key (128 caracteres)
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(64))"

# DB Password
openssl rand -base64 32

# Redis Password
openssl rand -base64 32
```

### 4. Iniciar con Docker Compose

```bash
# Iniciar todos los servicios
docker compose -f docker-compose.prod.yml up -d --build

# Ver logs
docker compose -f docker-compose.prod.yml logs -f

# Estado de servicios
docker compose -f docker-compose.prod.yml ps

# Validar el render final del compose
docker compose -f docker-compose.prod.yml config
```

### 5. Acceder a la aplicación

```
🔒 HTTPS: https://localhost/login
❌ HTTP: http://localhost (redirige a HTTPS)
📊 PgAdmin: http://127.0.0.1:5050  (solo si se levanta con --profile admin)
```

**Nota:** Navegador mostrará ⚠️ "Conexión no segura" (certificado autofirmado). Aceptar para continuar.

---

## 🔐 **SSL/TLS Certificados**

### Certificados autofirmados (desarrollo/testing)

Ya incluyen:
```
certs/cert.pem  ← Certificado público
certs/key.pem   ← Clave privada
```

### Certificados reales (producción)

**Opción 1: Let's Encrypt (GRATIS)**
```bash
docker-compose exec nginx certbot certonly --webroot -w /app/static -d tu-dominio.com
```

**Opción 2: Certificado comercial**
- Comprar en proveedor (DigiCert, Comodo, etc.)
- Reemplazar cert.pem y key.pem
- Reiniciar Nginx

---

## 📊 **Arquitectura de Servicios**

```
Internet
   ↓
[Nginx (ports 80/443)]
   ├─ HTTPS Certificate ✅
   ├─ Rate Limiting ✅
   ├─ Reverse Proxy ✅
   └─ Security Headers ✅
   ↓
[Flask App (port 3000)]
   ├─ JWT Authentication ✅
   ├─ Rate Limiting ✅
   └─ Admin Panel ✅
   ↓
[PostgreSQL (port 5432)]    [Redis (port 6379)]
   Database                    Sessions/Cache
```

---

## 🌐 **Configuración en Servidor Remoto**

### Publicación segura de la web

La aplicación Flask no debe exponerse directamente a Internet. En este repositorio, el servicio `web_app` queda ligado a `127.0.0.1:3000`, lo que obliga a publicarlo solo a través de un reverse proxy.

Ruta recomendada:

1. Mantener `web_app` privado en `127.0.0.1:3000`.
2. Abrir al exterior únicamente `80/443` en el servidor.
3. Terminar TLS en un reverse proxy del host o, si prefieres, levantar el perfil `edge` del compose.
4. No exponer `3000`, `5432` ni `6379` a Internet.

Ejemplo mínimo de Nginx del host:

```nginx
server {
   listen 80;
   server_name TU_DOMINIO;
   return 301 https://$host$request_uri;
}

server {
   listen 443 ssl http2;
   server_name TU_DOMINIO;

   ssl_certificate /etc/letsencrypt/live/TU_DOMINIO/fullchain.pem;
   ssl_certificate_key /etc/letsencrypt/live/TU_DOMINIO/privkey.pem;

   location / {
      proxy_pass http://127.0.0.1:3000;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
   }
}
```

Si quieres usar el Nginx del propio repositorio como edge proxy:

```bash
docker compose -f docker-compose.prod.yml --profile edge up -d nginx
```

Ese perfil publica `80/443` y reenvía tráfico a `web_app`, pero igual debes mantener `web_app` solo en loopback y filtrar el firewall del servidor.

### AWS EC2 / DigitalOcean / Linode

#### 1. SSH al servidor
```bash
ssh ubuntu@tu-IP-publica
```

#### 2. Instalar Docker y Docker Compose
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
   "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
   $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

#### 3. Clonar y setup
```bash
git clone <tu-repo> /opt/labeling-app
cd /opt/labeling-app
cp envs/production.env.example envs/production.env
chmod 600 envs/production.env
nano envs/production.env  # Editar con valores seguros
```

#### 4. Configurar firewall
```bash
# Abrir puertos
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

#### 5. Iniciar servicios
```bash
docker compose -f docker-compose.prod.yml up -d --build

# Ver logs
docker compose -f docker-compose.prod.yml logs -f web_app
```

#### 6. Verificar que funciona
```bash
curl -k https://tu-dominio.com/login
```

### Reimportación segura de un proyecto

Para limpiar y reimportar un proyecto sin volver a duplicar filas, usa el script operativo:

```bash
scripts/reimport_project_safe.sh --project-id memoria_1970_1990 --print-proxy-guide
```

Ese script:

- comprueba que `postgres`, `redis` y `web_app` estén activos,
- guarda un respaldo lógico del proyecto,
- limpia filas previas salvo que indiques `--skip-clean`,
- reimporta con el importador idempotente,
- y vuelve a imprimir la guía para levantar la web pública solo detrás de reverse proxy.

---

## 🔄 **Scaling Horizontal (Múltiples instancias)**

### Con Docker Swarm

```bash
# Inicializar Swarm
docker swarm init

# Deploy stack de producción
docker stack deploy -c docker-compose.prod.yml labeling_app

# Escalar Flask (replicar)
docker service scale labeling_app_web_app=3

# Ver estado
docker service ls
docker ps
```

### Con Kubernetes (k8s)

Ver: [PHASE3_KUBERNETES.md](./PHASE3_KUBERNETES.md)

---

## 📈 **Monitoreo y Alertas**

### Health Check
```bash
# Todos los servicios reportan estado
curl -f http://127.0.0.1:3000/health
curl -k https://localhost/health
```

### Logs centralizados
```bash
# Ver logs en tiempo real
docker-compose -f docker-compose.prod.yml logs -f

# Logs persistentes en
./logs/
./logs/nginx/
```

### Métricas
- PostgreSQL: PgAdmin en http://localhost:5050
- Redis: Redis Commander (opcional, agregar a docker-compose)

---

## 🔄 **Backup y Recuperación**

### Backup automático
```bash
# Ya configurado en app.py (BACKUP_ENABLED=True)
# Se ejecuta diariamente a las 2 AM

# Backups manuales
mkdir -p /home/cdgutierrez2/backups/labeling_app
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U "$DB_USER" "$DB_NAME" > /home/cdgutierrez2/backups/labeling_app/backup-$(date +%Y%m%d).sql

# Restaurar
docker compose -f docker-compose.prod.yml exec -T postgres psql -U "$DB_USER" "$DB_NAME" < /home/cdgutierrez2/backups/labeling_app/backup-20260413.sql
```

---

## 🚨 **Troubleshooting**

### Nginx no inicia
```bash
docker compose -f docker-compose.prod.yml logs nginx

# Validar config
docker compose -f docker-compose.prod.yml exec nginx nginx -t
```

### PostgreSQL connection error
```bash
# Verificar variables en envs/production.env
docker compose -f docker-compose.prod.yml logs postgres

# Verificar compose renderizado
docker compose -f docker-compose.prod.yml config
```


---

## 📌 Guia Para Jumbita

La guia exacta de dependencias del host y el texto para pedir permisos al admin quedó en:

`JUMBITA_SETUP.md`

Esa guia cubre:

- dependencias a instalar en el host jumbita;
- dependencias dentro del contenedor web;
- stack minimo para multiples consultas en produccion;
- mensaje exacto para pedir Docker o PostgreSQL al admin.

### Resetear BD
```bash
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up postgres
```

### Flask no responde
```bash
# Ver logs
docker compose -f docker-compose.prod.yml logs web_app

# Reiniciar
docker compose -f docker-compose.prod.yml restart web_app
```

---

## ✅ **Checklist Pre-Producción**

```
[ ] Cambiar todos JWT_SECRET_KEY, SECRET_KEY, DB_PASSWORD, REDIS_PASSWORD
[ ] Generar certificados reales (Let's Encrypt)
[ ] Configurar backups automáticos
[ ] Verificar rate limiting activo
[ ] Configurar monitoreo/alertas
[ ] Verificar SSL/TLS en navegador
[ ] Probar login y admin panel
[ ] Verificar base de datos persiste
[ ] Configurar dominio/DNS
[ ] Revisar security headers (HSTS, CSP, etc)
[ ] Probar scaling horizontal
[ ] Documentar credenciales en lugar seguro
[ ] Configurar CI/CD pipeline
```

---

## 📚 **Documentación Relacionada**

- [KEY_MANAGEMENT.md](./KEY_MANAGEMENT.md) - Gestión de secretos
- [ROBUSTNESS_CHECKLIST.md](./ROBUSTNESS_CHECKLIST.md) - Verificación de seguridad
- [DEPLOYMENT_PRODUCTION.md](./DEPLOYMENT_PRODUCTION.md) - Detalles adicionales

---

## 🆘 **Soporte**

Para problemas o preguntas:
1. Revisar logs: `docker-compose logs -f`
2. Verificar .env variables
3. Revisar documentación en `/doc`
4. GitHub Issues: `tu-repo/issues`

---

**Última actualización:** Abril 13, 2026  
**Version:** Phase 2 Production Ready
