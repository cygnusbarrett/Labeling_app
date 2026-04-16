# 🎯 Labeling App — Validación de Transcripciones de Audio

Sistema colaborativo para validación manual de transcripciones automáticas de audio, con panel administrativo, autenticación JWT y arquitectura lista para producción con Docker.

## 🚀 Inicio Rápido

### Desarrollo Local

```bash
# Clonar y entrar
git clone <repo-url> && cd Labeling_app

# Entorno virtual
python3 -m venv .venv && source .venv/bin/activate

# Dependencias
pip install -r src/requirements/requirements.txt

# Configurar entorno
cp envs/web_app.env.example envs/web_app.env
nano envs/web_app.env   # editar claves

# Iniciar
cd src && python app.py
```

Acceder en http://localhost:3000 — credenciales por defecto: `admin / admin123`

### Producción (Docker)

```bash
cp envs/web_app.env.example envs/web_app.env
nano envs/web_app.env   # Generar secretos reales (ver KEY_MANAGEMENT.md)
docker compose -f docker-compose.prod.yml up -d
```

Ver guía completa: [DEPLOYMENT_DOCKER_SETUP.md](DEPLOYMENT_DOCKER_SETUP.md)

## 📁 Estructura del Proyecto

```
Labeling_app/
├── src/                      # Código fuente
│   ├── app.py               # Aplicación Flask (entrada principal)
│   ├── config.py             # Configuración
│   ├── models/               # Modelos de base de datos
│   ├── routes/               # API endpoints
│   ├── services/             # Lógica de negocio
│   ├── static/               # Frontend (JS, CSS)
│   ├── templates/            # HTML (Jinja2)
│   ├── scripts/              # Utilidades (crear usuarios, importar datos)
│   └── requirements/         # Dependencias Python
├── docker/                   # Configuración Docker
│   ├── web_app/Dockerfile    # Imagen de la aplicación
│   └── nginx/nginx-prod.conf # Reverse proxy
├── envs/                     # Templates de variables de entorno
├── certs/                    # Certificados SSL
├── scripts/                  # Scripts de deployment
├── docker-compose.prod.yml   # Orquestación producción
└── archived-docs/            # Documentación de fases anteriores
```

## 🏗️ Arquitectura

```
  [Nginx :80/:443] → SSL, headers, rate limiting
         ↓
  [Flask/Gunicorn :3000] → JWT auth, admin panel, API
         ↓
  [PostgreSQL :5432]  [Redis :6379]
```

- **Backend:** Flask + Gunicorn
- **BD:** SQLite (dev) / PostgreSQL (prod)
- **Cache/Sesiones:** Redis
- **Proxy:** Nginx con SSL/TLS
- **Auth:** JWT con roles (admin / annotator)
- **Contenedores:** Docker Compose

## 📖 Documentación

| Documento | Descripción |
|-----------|-------------|
| [DEPLOYMENT_DOCKER_SETUP.md](DEPLOYMENT_DOCKER_SETUP.md) | Guía de deployment con Docker |
| [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) | Checklist pre/post deployment |
| [SECURITY.md](SECURITY.md) | Políticas de seguridad |
| [KEY_MANAGEMENT.md](KEY_MANAGEMENT.md) | Gestión de secretos y rotación |
| [src/README.md](src/README.md) | Documentación técnica del código |

Documentación histórica en [archived-docs/](archived-docs/).

## 🔐 Seguridad

Este repositorio **NO** contiene secretos reales. Generar antes de producción:

```bash
python3 -c "import secrets; print(secrets.token_hex(64))"   # JWT_SECRET_KEY
openssl rand -base64 32                                       # DB_PASSWORD, REDIS_PASSWORD
```

Ver: [KEY_MANAGEMENT.md](KEY_MANAGEMENT.md) y [SECURITY.md](SECURITY.md)

## 📄 Licencia

Ver [LICENSE](src/LICENSE)</content>
<parameter name="filePath">/Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/README.md