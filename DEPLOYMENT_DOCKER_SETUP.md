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
# Copiar el archivo de producción
cp .env.production .env

# Editar con tus valores seguros
nano .env
```

**Campos críticos a cambiar:**
```env
DB_PASSWORD=cambiar_esto_por_valor_seguro
REDIS_PASSWORD=cambiar_esto_por_valor_seguro
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
docker-compose -f docker-compose.prod.yml up -d

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f

# Estado de servicios
docker-compose -f docker-compose.prod.yml ps
```

### 5. Acceder a la aplicación

```
🔒 HTTPS: https://localhost:3000/login
❌ HTTP: http://localhost:3000 (redirige a HTTPS)
📊 PgAdmin: http://localhost:5050
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

### AWS EC2 / DigitalOcean / Linode

#### 1. SSH al servidor
```bash
ssh ubuntu@tu-IP-publica
```

#### 2. Instalar Docker y Docker Compose
```bash
curl -fsSL https://get.docker.com -o get-docker.sh | sh
sudo usermod -aG docker $USER
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

#### 3. Clonar y setup
```bash
git clone <tu-repo> /opt/labeling-app
cd /opt/labeling-app
cp .env.production .env
nano .env  # Editar con valores seguros
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
docker-compose -f docker-compose.prod.yml up -d

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f web_app
```

#### 6. Verificar que funciona
```bash
curl -k https://tu-dominio.com/login
```

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
curl https://localhost:3000/health
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
docker-compose exec postgres pg_dump -U labeling_app labeling_app > backup-$(date +%Y%m%d).sql

# Restaurar
docker-compose exec -T postgres psql -U labeling_app labeling_app < backup-20260413.sql
```

---

## 🚨 **Troubleshooting**

### Nginx no inicia
```bash
docker-compose -f docker-compose.prod.yml logs nginx

# Validar config
docker-compose exec nginx nginx -t
```

### PostgreSQL connection error
```bash
# Verificar contraseña en .env
docker-compose -f docker-compose.prod.yml logs postgres

# Resetear BD
docker-compose down -v
docker-compose -f docker-compose.prod.yml up postgres
```

### Flask no responde
```bash
# Ver logs
docker-compose -f docker-compose.prod.yml logs web_app

# Reiniciar
docker-compose restart web_app
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
