# 🎯 PRODUCTION CHECKLIST & MONITORING

## pre-Deployment Checklist

### 🔐 Seguridad

- [ ] **JWT_SECRET_KEY** - Generado con `python3 -c "import secrets; print(secrets.token_hex(64))"`
- [ ] **SECRET_KEY** - Generado con `python3 -c "import secrets; print(secrets.token_hex(64))"`
- [ ] **DB_PASSWORD** - Generado con `openssl rand -base64 32`
- [ ] **REDIS_PASSWORD** - Generado con `openssl rand -base64 32`
- [ ] **PGADMIN_PASSWORD** - Generado con contraseña aleatoria
- [ ] Certificados SSL reales adquiridos o Let's Encrypt configurado
- [ ] No hay secrets commiteados a git (revisar .gitignore)
- [ ] `.env` archivo NO está en repositorio (está en .gitignore)

### 📦 Configuración de Docker

- [ ] Docker instalado y ejecutándose
- [ ] Docker Compose v2+ instalado
- [ ] Directorios necesarios existen:
  - [ ] `certs/`
  - [ ] `logs/`
  - [ ] `src/logs/`
  - [ ] `data/backups/`
  - [ ] `data/transcription_projects/`
- [ ] Dockerfile actualizado (con Gunicorn, puerto 3000, healthchecks)
- [ ] docker-compose.prod.yml valida sintaxis

### 🗄️ Base de Datos

- [ ] PostgreSQL versión compatible (18-alpine)
- [ ] Schema inicializado (init-db.sql)
- [ ] Conexión desde Flask probada
- [ ] Backups automáticos configurados
- [ ] Credenciales DB seguros (no iguales a desarrollo)
- [ ] Redis configurado con contraseña
- [ ] Persistencia de datos habilitada (volumes)

### 🚀 Servidor

- [ ] Nginx configurado para HTTPS
- [ ] SSL/TLS protocols correctos (TLSv1.2, TLSv1.3)
- [ ] Security headers presentes:
  - [ ] HSTS (Strict-Transport-Security)
  - [ ] CSP (Content-Security-Policy)
  - [ ] X-Frame-Options: SAMEORIGIN
  - [ ] X-Content-Type-Options: nosniff
  - [ ] Referrer-Policy: strict-origin-when-cross-origin
- [ ] GZIP compression habilitada
- [ ] Rate limiting configurada en Nginx
- [ ] Health check endpoints configurados

### 🔍 Monitoreo

- [ ] Logs persistidos en `./logs/`
- [ ] Configuración de rotación de logs
- [ ] PgAdmin accesible en puerto 5050
- [ ] Redis CLI accesible
- [ ] Metrics collection habilitado (opcional)

### 🌐 Networking

- [ ] Puertos permitidos en firewall (80, 443)
- [ ] SSH habilitado solo en redes confiables
- [ ] DNS apunta a IP pública del servidor
- [ ] CNAME/A records correctamente configurados

### 📝 Documentación

- [ ] README actualizado con instrucciones deployment
- [ ] Credenciales guardadas en gestor seguro (1Password, Vault, etc.)
- [ ] Plan de backup/restore documentado
- [ ] Escalado horizontal documentado
- [ ] Runbook de troubleshooting disponible

---

## ✅ Post-Deployment Verification

### Verificación Inmediata

```bash
# 1. Verificar servicios activos
docker-compose -f docker-compose.prod.yml ps

# Esperado:
# STATUS: Up (healthy)
# NAME: nuestra-memoria-postgres ✓
# NAME: nuestra-memoria-redis ✓
# NAME: nuestra-memoria-flask ✓
# NAME: nuestra-memoria-nginx ✓

# 2. Verificar conectividad
curl -k https://localhost:3000/login
curl -k https://localhost/login
curl http://localhost/health

# 3. Ver logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Verificación Funcional

- [ ] **Admin Login**: Acceder a https://tu-dominio.com/admin/dashboard
- [ ] **User Creation**: Crear nuevo usuario desde admin panel
- [ ] **Annotator Access**: Login con usuario anotador
- [ ] **Transcription Upload**: Subir archivo de transcripción
- [ ] **Labeling**: Etiquetar palabras/segmentos
- [ ] **Export**: Exportar datos etiquetados
- [ ] **Database**: Conectar PgAdmin, verificar tablas
- [ ] **SSL Certificate**: Verificar que navegador no muestre warning

### Pruebas de Carga

```bash
# Instalar ab (Apache Bench) si no está disponible
brew install httpd  # macOS
apt-get install apache2-utils  # Linux

# Prueba de 1000 requests
ab -n 1000 -c 10 -k https://tu-dominio.com/

# Prueba de conexión SSL
openssl s_client -connect tu-dominio.com:443 -tls1_2
```

---

## 📊 Monitoreo en Producción

### Métricas Clave

#### Flask Application
```
- Requests/segundo
- Error rate (5xx errors)
- Response time (p50, p95, p99)
- Errores de autenticación
- Rate limit hits
```

#### PostgreSQL
```bash
# Ver conexiones activas
docker-compose exec postgres psql -U labeling_app -c "SELECT count(*) FROM pg_stat_activity;"

# Ver size de BD
docker-compose exec postgres psql -U labeling_app -c "SELECT pg_size_pretty(pg_database_size('labeling_app'));"

# Ver queries lentas
docker-compose exec postgres psql -U labeling_app -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

#### Redis
```bash
# Ver información del servidor
docker-compose exec redis redis-cli INFO

# Ver uso de memoria
docker-compose exec redis redis-cli INFO memory

# Ver conexiones
docker-compose exec redis redis-cli INFO clients
```

#### Nginx
```bash
# Ver conexiones activas
docker-compose exec nginx curl -s http://localhost/nginx_status

# Ver logs de acceso
tail -f ./logs/nginx/access.log

# Ver logs de error
tail -f ./logs/nginx/error.log
```

### Alertas Recomendadas

| Métrica | Umbral | Acción |
|---------|--------|--------|
| CPU > 80% | 5 min | Escalar poderes workers |
| Memoria > 85% | 5 min | Revisar memory leaks |
| Errores 5xx > 1% | 1 min | Revisar logs, escalar |
| Response time p99 > 5s | 5 min | Optimizar queries |
| Conexiones BD > 90% | 5 min | Aumentar pool size |
| Espacio disco < 10% | 24 h | Limpiar backups viejos |
| SSL cert expira < 30 días | 1 vez/día | Renovar certificado |

### Comandos de Monitoreo

```bash
# Monitoreo en tiempo real
watch -n 1 'docker stats --no-stream'

# Ver logs de todos los servicios
docker-compose -f docker-compose.prod.yml logs -f --tail=100

# Ver logs de servicio específico
docker-compose -f docker-compose.prod.yml logs -f web_app

# Estadísticas de Nginx
docker-compose exec nginx nginx -s reload  # Reload sin downtime

# Backup manual
docker-compose exec postgres pg_dump -U labeling_app labeling_app > backup-$(date +%Y%m%d-%H%M%S).sql

# Restaurar backup
docker-compose exec -T postgres psql -U labeling_app labeling_app < backup-20260413.sql
```

---

## 🆘 Troubleshooting Guía Rápida

### Problema: Nginx no inicia

```bash
# Ver logs
docker-compose logs nginx

# Validar configuración
docker-compose exec nginx nginx -t

# Reiniciar
docker-compose restart nginx
```

### Problema: Flask crashes

```bash
# Ver logs
docker-compose logs web_app

# Verificar variables de entorno
docker-compose exec web_app env | grep -E "DB|REDIS|JWT"

# Revisar requirements
docker-compose exec web_app pip list | grep -E "flask|psycopg2|redis"

# Reiniciar
docker-compose restart web_app
```

### Problema: PostgreSQL no conecta

```bash
# Ver logs
docker-compose logs postgres

# Verificar contraseña en .env
grep DB_PASSWORD .env

# Test conexión
docker-compose exec postgres psql -U labeling_app -h localhost

# Reiniciar
docker-compose restart postgres
```

### Problema: HTTPS certificate warning

**LOCAL (desarrollo):** Es normal, certificado autofirmado
**PRODUCCIÓN:** Adquirir certificado real o usar Let's Encrypt

```bash
# Verificar certificado
openssl x509 -in ./certs/cert.pem -text -noout

# Verificar expiración
openssl x509 -enddate -noout -in ./certs/cert.pem
```

### Problema: Redis connection refused

```bash
# Verificar password
grep REDIS_PASSWORD .env

# Test conexión
docker-compose exec redis redis-cli -a "$(grep REDIS_PASSWORD .env | cut -d= -f2)" ping

# Ver logs
docker-compose logs redis
```

---

## 🔄 Mantenimiento Regular

### Diariamente
- [ ] Revisar logs de errores
- [ ] Monitorear uso de recursos
- [ ] Verificar backups se ejecutaron

### Semanalmente
- [ ] Revisar métrica de performance
- [ ] Validar salud de servicios
- [ ] Test restore de backup

### Mensualmente
- [ ] Revisar y limpiar logs antiguos
- [ ] Actualizar dependencias (si aplica)
- [ ] Audit de acceso y seguridad
- [ ] Renovar tokens si es necesario

### Anualmente
- [ ] Renovar certificado SSL
- [ ] Full backup restore test
- [ ] Security audit
- [ ] Capacity planning review

---

## 📞 Escaladation Path

1. **Revisar logs:**
   ```bash
   docker-compose logs -f --tail=200
   ```

2. **Verificar servicios:**
   ```bash
   docker-compose ps
   ```

3. **Reiniciar servicio problemático:**
   ```bash
   docker-compose restart <service>
   ```

4. **Reiniciar todos los servicios:**
   ```bash
   docker-compose down && docker-compose up -d
   ```

5. **Contactar soporte:**
   - Incluir: Logs completos, error messages, contexto
   - Archivo: `logs/error.log`, `logs/nginx/error.log`

---

**Última actualización:** Abril 13, 2026
**Versión:** Phase 3 Production Setup
