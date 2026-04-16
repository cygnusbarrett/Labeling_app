# 🔐 Security Checklist para Producción

> Antes de deployar a producción, completar todas estas verificaciones

---

## 🔑 Secretas y Credenciales

- [ ] JWT_SECRET_KEY es único y tiene ≥32 caracteres aleatorios
- [ ] SECRET_KEY es único y tiene ≥32 caracteres aleatorios
- [ ] Contraseña PostgreSQL tiene ≥16 caracteres y caracteres especiales
- [ ] Contraseña de admin cambiada desde `admin123` por defecto
- [ ] Todas las secretas están en variables de entorno (NO en código)
- [ ] `.env` files nunca están commiteadas a git
- [ ] `FLASK_ENV=production` en servidor

## 🔒 Base de Datos

- [ ] Usando PostgreSQL en producción (NO SQLite)
- [ ] PostgreSQL corriendo en contenedor con volumen persistente
- [ ] Credenciales PostgreSQL son únicas por instancia
- [ ] Backups configurados y testeados
- [ ] Replicación standby configurada (si HA requerido)
- [ ] Firewall restricts acceso a DB (solo desde app container)
- [ ] Usuario PostgreSQL tiene permisos mínimos necesarios

## 🌐 HTTPS/SSL

- [ ] Certificado SSL valido (Let's Encrypt o CA)
- [ ] HTTP redirect a HTTPS configurado en Nginx
- [ ] SSL protocols: TLSv1.2 mínimo
- [ ] HSTS headers configurados (`max-age=31536000`)
- [ ] Perfect Forward Secrecy (PFS) habilitado
- [ ] Certificado será renovado automáticamente pre-expiración

## 🚥 Rate Limiting

- [ ] Login: máximo 5 intentos en 15 minutos
- [ ] API submissions: máximo 60 por minuto
- [ ] General API: máximo 100 por minuto
- [ ] DDoS protection configurado en Nginx

## 🖥️ API Security

- [ ] Rate limiting en todos endpoints POST
- [ ] Input validation con Marshmallow schemas
- [ ] SQL injection: imposible (usando SQLAlchemy ORM)
- [ ] CSRF tokens en formularios (si aplica)
- [ ] CORS configurado restrictivamente
- [ ] X-Content-Type-Options: nosniff
- [ ] X-Frame-Options: SAMEORIGIN
- [ ] Content-Security-Policy headers

## 🔐 Authentication & Authorization

- [ ] JWT tokens tienen expiración (60 min acceso, 30 días refresh)
- [ ] Refresh tokens solo se emiten en login exitoso
- [ ] Tokens se validan en cada request
- [ ] Roles (admin, annotator) se verifican en endpoints
- [ ] Session cookies tienen flags: HttpOnly, Secure, SameSite=Strict

## 📊 Logging & Monitoring

- [ ] Logging configurado en INFO level (NO DEBUG en producción)
- [ ] Logs rotados automáticamente (RotatingFileHandler)
- [ ] Sensible data NO se loguea (passwords, tokens)
- [ ] Acceso a admin endpoints se loguea
- [ ] Failuras de login se monitorean
- [ ] Health checks activos cada 60 segundos
- [ ] Alertas Telegram configuradas para eventos críticos

## 🐳 Docker & Containers

- [ ] Images son de registros oficiales (python:3.10-slim, postgres:15)
- [ ] Containers corren como non-root user
- [ ] Permisos de archivos: 755 para dirs, 644 para files
- [ ] Secrets NO están hardcodeadas en Dockerfile
- [ ] Health checks configurados en docker-compose
- [ ] Restart policy: `always` para servicos críticos
- [ ] Resource limits: CPU y memory configurados

## 🔥 Firewall & Network

- [ ] Solo puertos 80, 443 expuestos públicamente
- [ ] PostgreSQL no expuesto a internet (solo internal network)
- [ ] Redis (si usado) não expuesto a internet
- [ ] Whitelist de IPs para admin endpoints (si aplica)
- [ ] DDoS protection en nivel de ISP/CDN

## 📦 Dependencies

- [ ] `requirements.txt` pinned a versiones específicas
- [ ] Sin dependencias deprecated o con vulnerabilidades conocidas
- [ ] Revisar `pip audit` para CVEs
- [ ] Security updates aplicados mensualmente

## 🚀 Deployment Process

- [ ] Blue-green deployment strategy
- [ ] Rollback plan documentado
- [ ] Database migrations testeadas antes
- [ ] Health check de 5 minutos post-deployment
- [ ] Runbook de incidentes creado
- [ ] Equipo capacitado en procedures

## 🚨 Incident Response

- [ ] Contacto de emergencia documentado
- [ ] Procedure para breach da dados definida
- [ ] Backup restore planificado & testeado
- [ ] Communication plan para usuarios si outage

## 📋 Compliance

- [ ] Privacy policy acorde a GDPR/local regs
- [ ] User data encryption en rest (DB)
- [ ] User data encryption in transit (HTTPS)
- [ ] Audit trail de cambios importante (quién editó qué cuándo)
- [ ] Deletion de datos testeable

## ✅ Pre-Go-Live Checklist

```bash
# 1. Security scan local
docker run --rm -i aquasec/trivy:latest image web_app:latest

# 2. Test SSL configuration
nmap --script ssl-enum-ciphers -p 443 transcriptions.domain.com

# 3. Penetration test básico
# - Login brute force (should get rate-limited)
# - SQL injection en fields
# - XSS en text fields  
# - CSRF token validation

# 4. Load test
ab -n 1000 -c 50 https://transcriptions.domain.com/api/v2/health

# 5. Backup restore test
# Restaurar desde backup y verificar integridad

# 6. Failover test
# Simular falla de worker y verificar que otros sirven requests
```

---

**IMPORTANTE:** 
- ⚠️ NO deployar sin completar esta checklist
- 🔐 Revisar quarterly o cuando cambien versiones de dependencias
- 📞 Contactar security team si hay duda en cualquier punto

**Última revisión:** Abril 2026
