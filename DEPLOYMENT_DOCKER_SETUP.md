# 🚀 DEPLOYMENT GUIDE - PRODUCTION SETUP

## 📋 Descripción

Este proyecto está configurado para deployarse en producción con:
- ✅ **Nginx** - Reverse proxy con SSL/TLS
- ✅ **Flask** - Servidor de aplicación
- ✅ **PostgreSQL** - Base de datos persistente
- ✅ **Redis** - Cache, sesiones distribuidas y backend compartido para rate limiting
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

### 2.1. Ajustar inputs del host en un solo script

Los paths editables por usuario ya no se reparten entre varios archivos. Quedaron centralizados en [scripts/runtime_config.sh](/Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/scripts/runtime_config.sh).

Si cambian directorios del servidor, corrige solo ese archivo:

```bash
nano scripts/runtime_config.sh
```

Los campos que normalmente tendrás que tocar ahí son:

```bash
HOST_DOCKER_PROJECTS=/home/cdgutierrez2/docker_projects
HOST_DOCKER_DATA=/home/cdgutierrez2/docker_data
HOST_BACKUPS=/home/cdgutierrez2/backups
HOST_TRANSCRIPT_SOURCE=/home/cdgutierrez2/transcripciones
HOST_AUDIO_SOURCE=/home/cdgutierrez2/solo_es_73-90

TRANSCRIPTION_PROJECTS_PATH=/app/data/transcription_projects
TRANSCRIPT_SOURCE_PATH=/app/data/transcriptions
AUDIO_FILES_PATH=/app/data/audio_source
UPLOADS_PATH=/app/data/uploads
```

**Campos críticos a cambiar:**
```env
POSTGRES_ADMIN_USER=cdgutierrez2
POSTGRES_ADMIN_PASSWORD=cambiar_esto_por_valor_seguro
APP_DB_USER=labeling_app
APP_DB_PASSWORD=cambiar_esto_por_valor_seguro
DB_NAME=labeling_db
REDIS_PASSWORD=cambiar_esto_por_valor_seguro
DATABASE_URL=postgresql://labeling_app:cambiar_esto_por_valor_seguro@postgres:5432/labeling_db
REDIS_URL=redis://:cambiar_esto_por_valor_seguro@redis:6379

La aplicación usa `REDIS_URL` tanto para sesiones distribuidas como para el estado compartido del rate limiting. Con esto, los límites se mantienen consistentes entre workers del mismo contenedor y no se pierden en cada request como ocurría con almacenamiento puramente en memoria.

Los JWT activos del flujo web ya no se guardan en `localStorage`. El backend los emite como cookies `HttpOnly` (`access_token` y `refresh_token`) y las rutas activas del frontend usan requests same-origin más `/me` para obtener el usuario actual. Esto reduce exposición ante XSS sin depender de headers `Authorization` en las pantallas activas.
JWT_SECRET_KEY=cambiar_esto_por_valor_seguro_de_128_caracteres
SECRET_KEY=cambiar_esto_por_valor_seguro_de_128_caracteres
```

**Importante para el despliegue Docker en jumbita:**

- El servicio `web_app` del compose productivo no usa el fallback SQLite de `src/config.py` mientras arranque mediante [docker-compose.prod.yml](/Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/docker-compose.prod.yml), porque el propio compose le inyecta `DATABASE_URL=postgresql://...@postgres:5432/...`.
- En ese camino Docker, los valores realmente obligatorios son `POSTGRES_ADMIN_USER`, `POSTGRES_ADMIN_PASSWORD`, `APP_DB_USER`, `APP_DB_PASSWORD`, `DB_NAME`, `REDIS_PASSWORD`, `JWT_SECRET_KEY` y `SECRET_KEY` en `envs/production.env`.
- `POSTGRES_ADMIN_USER` es el administrador SQL del motor PostgreSQL. Puede ser `cdgutierrez2`.
- `APP_DB_USER` es el usuario técnico con el que se conecta Flask. No es un usuario humano.
- El admin funcional de la plataforma se mantiene como `admin / admin123`.
- Mantén `DATABASE_URL` también en `envs/production.env` para scripts operativos ejecutados fuera del contenedor y para evitar ambigüedad al depurar.
- Si cambias código del validador, no basta con reiniciar el contenedor: debes reconstruir la imagen con `docker compose -f docker-compose.prod.yml up -d --build` o el contenedor seguirá ejecutando la versión anterior horneada en la imagen.

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
# Ver resumen efectivo de paths y parametros operativos
bash scripts/run_production_stack.sh summary

# Iniciar todos los servicios usando la configuracion centralizada
bash scripts/run_production_stack.sh up

# Ver logs
bash scripts/run_production_stack.sh logs

# Estado de servicios
bash scripts/run_production_stack.sh ps

# Validar el render final del compose
bash scripts/run_production_stack.sh config
```

**Nota:** el código de la aplicación queda empaquetado dentro de la imagen de `web_app`. Si cambias archivos en `src/`, vuelve a ejecutar `docker compose -f docker-compose.prod.yml up -d --build` para que la prueba use exactamente ese commit.

### 4.1. Qué cambios funcionales deben verse dentro del contenedor

La imagen de producción debe incluir estos cambios del validador:

- limpieza del audio anterior antes de cargar el siguiente segmento
- espera del audio del segmento actual antes de mostrar la tarjeta
- recarga de la cola pendiente desde servidor al avanzar
- eliminación del botón `Repetir`
- bloque de audio debajo del bloque de transcripción
- botón `Confirmar con duda`
- persistencia de `decision_type` separada de `review_status`
- regeneración automática de `reconstructed_transcript.json` y `reconstructed_transcript.txt`

Verificación mínima recomendada después del `--build`:

```bash
# Render efectivo del compose
docker compose -f docker-compose.prod.yml config

# Confirmar que el contenedor quedó sano
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 web_app

# Smoke test HTTP
curl -I http://127.0.0.1:3000/health
curl -I http://127.0.0.1:3000/login
```

Si quieres forzar la reconstrucción manual de exportaciones ya dentro del contenedor:

```bash
docker compose -f docker-compose.prod.yml exec -u root web_app sh -lc '
chown -R appuser:appuser /app/data/transcription_projects/memoria_1970_1990
'

docker compose -f docker-compose.prod.yml exec web_app \
   python scripts/rebuild_transcription_exports.py --project-id memoria_1970_1990
```

Si el proyecto de transcripción viene de un bind mount del host, asegúrate de normalizar ownership y permisos desde el contenedor para que `web_app` pueda regenerar `reconstructed_transcript.json` y `reconstructed_transcript.txt`. El script [scripts/deploy_and_smoketest_jumbita.sh](/Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/scripts/deploy_and_smoketest_jumbita.sh) ya hace ese ajuste antes del smoke test.

Para no ejecutar estos pasos a mano en cada deploy de jumbita, usa el script [scripts/deploy_and_smoketest_jumbita.sh](/Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/scripts/deploy_and_smoketest_jumbita.sh). Ese script ahora carga automáticamente [scripts/runtime_config.sh](/Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/scripts/runtime_config.sh). La prueba manual del navegador quedó resumida en [JUMBITA_VALIDATOR_SMOKETEST.md](/Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/JUMBITA_VALIDATOR_SMOKETEST.md).

### 4.2. Bootstrap limpio de PostgreSQL desde cero

Si esta es la primera instalación real o quieres descartar por completo un volumen inconsistente, usa el script [scripts/bootstrap_fresh_postgres.sh](/Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/scripts/bootstrap_fresh_postgres.sh). El flujo recomendado es:

```bash
bash scripts/bootstrap_fresh_postgres.sh
```

Ese script hace lo siguiente:

- detiene el stack Docker productivo
- elimina solo el volumen/directorio persistente de PostgreSQL
- vuelve a levantar PostgreSQL, Redis y `web_app` con la configuración vigente
- deja creada la base vacía con el administrador SQL definido por `POSTGRES_ADMIN_USER`/`POSTGRES_ADMIN_PASSWORD`
- crea el rol técnico de la aplicación usando `APP_DB_USER`/`APP_DB_PASSWORD`
- mantiene el admin funcional de la plataforma como `admin / admin123`
- ejecuta la importación manual desde `TRANSCRIPT_SOURCE_PATH` y `AUDIO_FILES_PATH`

Patrón operativo recomendado:

- acceso directo a PostgreSQL: solo tu usuario operador/admin y el rol técnico de la app
- usuarios humanos del sistema: viven en la tabla `users` de la aplicación y los crea un admin funcional
- anotadores y revisores no necesitan acceso SQL directo

### 4.3. Actualización incremental desde directorios fuente

Cuando aparezcan nuevos pares JSON/audio en los directorios configurados, no necesitas recrear la base. Ejecuta:

```bash
bash scripts/import_runtime_sources.sh memoria_1970_1990
```

El importador quedó en modo aditivo:

- inserta proyectos, segmentos y palabras que aún no existen
- no modifica segmentos ya importados
- no reescribe decisiones ni correcciones existentes
- recalcula las estadísticas del proyecto a partir del estado real de la BD

### 4.4. Estado real respecto de los criterios actuales

Integrado:

- rate limiting compartido en Redis para no depender de memoria local por worker
- `ProxyFix` en Flask para respetar `X-Forwarded-*` cuando entre el reverse proxy
- JWT activos movidos a cookies `HttpOnly` en las pantallas hoy en uso
- `web_app`, PostgreSQL y Redis mantenidos en puertos privados del host (`127.0.0.1` donde corresponde)
- audio del validador servido desde el segmento correcto, con validaciones básicas de rango de tiempo en runtime

Pendiente o mantenido así a propósito:

- el admin funcional sigue siendo `admin / admin123` hasta cambiarlo antes de exposición pública
- no se agregó validación fuerte de exactitud transcript-audio más allá de evitar cruces obvios de archivo/rango
- el reverse proxy público final y TLS real siguen fuera de este ajuste; la guía está, pero su publicación depende del paso operativo externo
- no se ejecutó una prueba de carga real todavía
- quedan archivos legados/no activos que aún mencionan `localStorage` para JWT; no controlan el flujo vivo actual, pero conviene limpiarlos si luego quieres dejar el repo homogéneo


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

Ese `--build` no es opcional después de cambios de aplicación: el compose de producción ya no monta `src/` desde el host, justamente para que el contenedor ejecute el código horneado en la imagen.

Si `envs/production.env` fue copiado manualmente al servidor fuera de Git, verifica que siga existiendo antes del deploy y que contenga al menos `POSTGRES_ADMIN_USER`, `POSTGRES_ADMIN_PASSWORD`, `APP_DB_USER`, `APP_DB_PASSWORD`, `DB_NAME`, `REDIS_PASSWORD`, `JWT_SECRET_KEY` y `SECRET_KEY`. En el stack Docker, `DATABASE_URL` final del contenedor se calcula desde esos valores, pero conviene dejarla definida también en el archivo para cualquier script ejecutado en el host.

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
docker compose -f docker-compose.prod.yml exec postgres sh -lc 'export PGPASSWORD="$POSTGRES_PASSWORD"; pg_dump -h 127.0.0.1 -U "$POSTGRES_USER" "$POSTGRES_DB"' > /home/cdgutierrez2/backups/labeling_app/backup-$(date +%Y%m%d).sql

# Restaurar
docker compose -f docker-compose.prod.yml exec -T postgres sh -lc 'export PGPASSWORD="$POSTGRES_PASSWORD"; psql -h 127.0.0.1 -U "$POSTGRES_USER" "$POSTGRES_DB"' < /home/cdgutierrez2/backups/labeling_app/backup-20260413.sql
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
[ ] Cambiar todos JWT_SECRET_KEY, SECRET_KEY, POSTGRES_ADMIN_PASSWORD, APP_DB_PASSWORD, REDIS_PASSWORD
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
- [SECURITY.md](./SECURITY.md) - Controles y criterios de seguridad vigentes
- [PRODUCTION_CHECKLIST.md](./PRODUCTION_CHECKLIST.md) - Checklist operativo de despliegue

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
