# Jumbita Setup

Esta guia resume lo necesario para desplegar este proyecto de forma correcta en jumbita usando Docker, primero en puertos internos del host y despues detras del reverse proxy que configurara el admin.

## 1. Que si puedo y que no puedo habilitar hoy en `cdgutierrez2`

Con los permisos actuales de `cdgutierrez2` no puedo levantar un PostgreSQL local de servidor por mi cuenta si el host no tiene una de estas opciones disponibles:

1. Docker Engine con permisos para ejecutar `docker compose`.
2. Binarios del servidor PostgreSQL instalados en el host: `postgres`, `initdb`, `pg_ctl`, `psql`.
3. Una instancia PostgreSQL remota accesible desde jumbita.

Sin una de esas tres condiciones, solo puedo correr el proyecto con SQLite en modo de prueba.

## 2. Dependencias exactas a instalar en jumbita host

Si el despliegue sera con Docker, estas son las dependencias del host que conviene instalar:

### Imprescindibles

1. Docker Engine 24+.
2. Docker Compose Plugin v2.
3. Git.
4. Curl.
5. OpenSSL o certificados gestionados externamente.

### Recomendadas para operacion

1. `jq` para inspeccionar JSON y healthchecks.
2. `htop` para CPU y memoria.
3. `ncdu` para revisar consumo de disco.
4. `sysstat` para `iostat` y `pidstat`.
5. `logrotate` si fuera necesario rotar logs del host aparte de Docker.

### Instalacion sugerida en Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git jq htop ncdu sysstat openssl

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
newgrp docker
docker --version
docker compose version
```

## 3. Dependencias que quedaran dentro del contenedor web

El contenedor de la app deberia incluir, como minimo:

1. `build-essential`
2. `libpq-dev`
3. `postgresql-client`
4. `ffmpeg`
5. `libsndfile1`
6. `curl`
7. `git`
8. `tini`
9. `ca-certificates`

Motivo principal:

1. `ffmpeg` y `libsndfile1` mejoran el trabajo con audio real y reducen friccion con formatos y recortes.
2. `postgresql-client` sirve para validacion y debugging del servicio PostgreSQL.
3. `tini` mejora apagados limpios y manejo de procesos en contenedores.

## 4. Servicios minimos para soportar multiples consultas en jumbita

El stack minimo recomendado para este proyecto es:

1. Gunicorn con multiples workers.
2. PostgreSQL para concurrencia real y persistencia robusta.
3. Redis para sesiones distribuidas entre workers.
4. Volumenes persistentes para BD, Redis, logs y datos de proyecto.
5. Reverse proxy externo del admin apuntando al puerto interno de la app cuando la validacion local este lista.

## 5. Ajustes concretos recomendados en este repositorio

Estos son los cambios mas importantes ya preparados en el repo:

1. El contenedor web ahora arranca con `wsgi:app`, que es el entrypoint real de produccion.
2. Gunicorn toma `bind`, `workers`, `worker_class` y `timeout` desde `src/gunicorn_config.py` y variables de entorno, sin banderas contradictorias en el `Dockerfile`.
3. El healthcheck ahora usa `/health` en vez de `/login`.
4. PostgreSQL y Redis ya no quedan publicados a toda la red, solo a `127.0.0.1` del host.
5. Nginx del repositorio queda detras de un profile opcional `edge`, porque en jumbita el reverse proxy final lo manejara el admin.
6. PgAdmin queda detras de un profile opcional.
7. Se agregan dependencias de audio y runtime utiles para produccion.

## 6. Rutas persistentes del usuario en jumbita

Usaremos estas rutas del usuario `cdgutierrez2`:

```text
/home/cdgutierrez2/docker_projects
/home/cdgutierrez2/docker_data
/home/cdgutierrez2/backups
```

Estructura recomendada:

```text
/home/cdgutierrez2/docker_projects/Labeling_app
/home/cdgutierrez2/docker_data/postgres
/home/cdgutierrez2/docker_data/redis
/home/cdgutierrez2/docker_data/transcription_projects
/home/cdgutierrez2/docker_data/logs/web_app
/home/cdgutierrez2/docker_data/logs/nginx
/home/cdgutierrez2/docker_data/pgadmin
/home/cdgutierrez2/backups/labeling_app
```

Creacion inicial:

```bash
mkdir -p /home/cdgutierrez2/docker_projects
mkdir -p /home/cdgutierrez2/docker_data/postgres
mkdir -p /home/cdgutierrez2/docker_data/redis
mkdir -p /home/cdgutierrez2/docker_data/transcription_projects
mkdir -p /home/cdgutierrez2/docker_data/logs/web_app
mkdir -p /home/cdgutierrez2/docker_data/logs/nginx
mkdir -p /home/cdgutierrez2/docker_data/pgadmin
mkdir -p /home/cdgutierrez2/backups/labeling_app
```

## 7. Pedido exacto al admin

Puedes enviar este texto casi literal:

```text
Necesito habilitar un entorno Docker de desarrollo validado para Labeling_app en jumbita.

La app levantara PostgreSQL y Redis dentro de Docker, expuestos solo en puertos internos del host. Una vez validada localmente en el usuario cdgutierrez2, el reverse proxy quedara de su lado apuntando al puerto interno definido en Docker Compose.

Ademas necesito confirmar:
- que mi usuario cdgutierrez2 puede usar Docker Compose;
- que el reverse proxy apuntara despues a 127.0.0.1:3000 u otro puerto interno que dejemos definido;
- que la persistencia se hara bajo /home/cdgutierrez2/docker_projects, /home/cdgutierrez2/docker_data y /home/cdgutierrez2/backups.
```

## 8. Variables de entorno minimas para jumbita

Primero crea el archivo real de entorno:

```bash
cp envs/production.env.example envs/production.env
chmod 600 envs/production.env
```

Antes de levantar `docker compose`, define al menos estas variables:

```env
FLASK_ENV=development
DEBUG=False
DB_USER=labeling_user
DB_PASSWORD=colocar_password_fuerte
DB_NAME=labeling_db
DATABASE_URL=postgresql://labeling_user:colocar_password_fuerte@postgres:5432/labeling_db
REDIS_PASSWORD=colocar_password_fuerte
REDIS_URL=redis://:colocar_password_fuerte@redis:6379
JWT_SECRET_KEY=colocar_64_hex_fuertes
SECRET_KEY=colocar_64_hex_fuertes
HOST_DOCKER_PROJECTS=/home/cdgutierrez2/docker_projects
HOST_DOCKER_DATA=/home/cdgutierrez2/docker_data
HOST_BACKUPS=/home/cdgutierrez2/backups
PORT=3000
WORKERS=4
WORKER_CLASS=gthread
WORKER_TIMEOUT=120
```

## 9. Comandos de verificacion despues del despliegue

```bash
mkdir -p /home/cdgutierrez2/docker_projects
cd /home/cdgutierrez2/docker_projects
git clone <tu-repo> Labeling_app
cd Labeling_app
cp envs/production.env.example envs/production.env
chmod 600 envs/production.env

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f web_app
curl -f http://127.0.0.1:3000/health
```

Si quieres exponer PgAdmin localmente para debugging puntual:

```bash
docker compose -f docker-compose.prod.yml --profile admin up -d pgadmin
```

Si mas adelante quieres levantar tambien el Nginx del repositorio para pruebas locales, hazlo explicitamente:

```bash
docker compose -f docker-compose.prod.yml --profile edge up -d nginx
```