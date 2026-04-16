# 🎯 Labeling App — Validación Colaborativa de Transcripciones de Audio

Sistema web para validar y corregir transcripciones automáticas (ASR) de audio, diseñado para proyectos de memoria histórica. Los anotadores revisan segmentos de audio y corrigen solo las palabras que el modelo transcribió con baja confianza, minimizando errores involuntarios.

## ✨ Características Principales

- **Edición inline inteligente**: solo las palabras con baja confianza del ASR son editables; las seguras son estáticas (doble-click para desbloquear cualquiera)
- **Anti-sesgo**: campos vacíos con placeholder gris (no pre-llenados) para evitar anclaje cognitivo
- **Panel administrativo**: asignar/desasignar segmentos, ver progreso por anotador, estadísticas en tiempo real
- **Roles**: admin (gestiona + anota) y annotator (solo anota sus segmentos asignados)
- **Audio integrado**: reproducción del fragmento exacto de cada segmento
- **JWT auth**: autenticación stateless con refresh tokens
- **Docker-ready**: Nginx + Gunicorn + PostgreSQL + Redis para producción

---

## 🚀 Inicio Rápido (Desarrollo Local)

### Requisitos

- Python 3.9+
- Redis (para sesiones): `brew install redis && brew services start redis` (macOS) o `sudo apt install redis-server` (Linux)

### Instalación

```bash
# 1. Clonar
git clone https://github.com/tsunayoshi21/Labeling_app.git
cd Labeling_app

# 2. Entorno virtual
python3 -m venv .venv && source .venv/bin/activate

# 3. Dependencias
pip install -r src/requirements/requirements.txt

# 4. Configurar entorno (opcional para dev, usa defaults)
cp envs/web_app.env.example envs/web_app.env
```

### Preparar datos

Colocar los archivos de transcripción en:
```
src/data/transcription_projects/<project_id>/
  ├── metadata.json          (opcional: nombre y descripción del proyecto)
  ├── audio_file_1.wav       (archivo de audio)
  ├── audio_file_1.json      (transcripción Whisper con segments[])
  ├── audio_file_2.wav
  ├── audio_file_2.json
  └── ...
```

**Formato del JSON** (output de Whisper + diarización):
```json
{
  "segments": [
    {
      "start": 1.14,
      "end": 5.82,
      "text": "Bueno, y el informe de la Cámara...",
      "speaker": "SPEAKER_01",
      "words": [
        {
          "word": "Bueno,",
          "start": 1.14,
          "end": 1.88,
          "speaker": "SPEAKER_01",
          "probability": 0.868
        }
      ]
    }
  ]
}
```

> Los segmentos cuyas palabras tengan **probability < 0.95** quedan como `pending` para revisión manual. El resto se auto-aprueba.

### Inicializar y ejecutar

```bash
cd src/

# Crear BD e importar datos (¡borra BD existente!)
python init_and_import.py

# Crear usuarios anotadores
python scripts/create_user.py user1 contraseña123 annotator
python scripts/create_user.py user2 contraseña456 annotator

# Listar usuarios
python scripts/list_users.py

# Iniciar servidor (puerto 3000)
python app.py
```

Abrir http://localhost:3000 — login por defecto: `admin / admin123`

---

## 👤 Flujo de Uso

### Administrador

1. Login en http://localhost:3000/login
2. Panel admin (http://localhost:3000/admin/dashboard):
   - Ver segmentos pendientes y asignarlos a anotadores
   - Ver progreso por usuario (completados, pendientes)
   - Desasignar segmentos si es necesario
3. Navegar a "Mis Anotaciones" desde la barra superior para anotar también

### Anotador

1. Login con sus credenciales
2. Ve solo los segmentos asignados a él/ella
3. Para cada segmento:
   - Escucha el audio del fragmento
   - Las **palabras inciertas** aparecen como campos vacíos con texto gris (placeholder)
   - Si la palabra del ASR es correcta → dejar vacío
   - Si hay que corregir → escribir la corrección en el campo
   - Doble-click en cualquier palabra "segura" para editarla también
   - Click en **✓ Confirmar** para enviar
4. Al completar todos los segmentos → mensaje de felicitaciones 🎉

---

## 🏗️ Arquitectura

```
Desarrollo:
  [Browser] → [Flask :3000] → [SQLite] + [Redis :6379]

Producción:
  [Cloudflare/Nginx :443] → [Gunicorn :3000] → [PostgreSQL :5432] + [Redis :6379]
```

### Stack técnico

| Capa | Tecnología |
|------|-----------|
| Backend | Flask + Gunicorn |
| Base de datos | SQLite (dev) / PostgreSQL (prod) |
| Sesiones | Redis |
| Auth | JWT (access + refresh tokens) |
| Frontend | Vanilla JS (sin frameworks) |
| Proxy | Nginx con SSL/TLS |
| Deploy | Docker Compose |

### Estructura del proyecto

```
Labeling_app/
├── src/                          # Código fuente
│   ├── app.py                    # Entrada principal Flask
│   ├── config.py                 # Configuración (env vars)
│   ├── init_and_import.py        # Reset BD + importar datos
│   ├── models/database.py        # Modelos SQLAlchemy (User, Segment, Word, Project)
│   ├── routes/
│   │   ├── sqlite_api_routes_jwt.py  # Auth: login, refresh, logout
│   │   ├── admin_api_routes.py       # API admin: asignar, desasignar, stats
│   │   └── transcription_api_routes.py # API anotación: palabras, submit, audio
│   ├── services/                 # Lógica de negocio (audio, DB, rate limit)
│   ├── static/js/
│   │   ├── services/             # API clients (transcriptionService, adminService)
│   │   └── controllers/          # UI controllers (transcription, adminDashboard)
│   ├── templates/                # HTML (login, validator, admin dashboard)
│   ├── scripts/                  # CLI: create_user, list_users, import_segments
│   └── data/transcription_projects/  # Audio WAV + JSON por proyecto
├── docker/                       # Dockerfiles y configs (nginx, postgres, web_app)
├── envs/                         # Templates de variables de entorno
├── docker-compose.prod.yml       # Orquestación producción
├── DEPLOYMENT_DOCKER_SETUP.md    # Guía de deployment Docker
├── SECURITY.md                   # Políticas de seguridad
├── KEY_MANAGEMENT.md             # Gestión de secretos
└── PRODUCTION_CHECKLIST.md       # Checklist pre-deployment
```

### Modelo de datos

```
TranscriptionProject (1) ──→ (N) Segment (1) ──→ (N) Word
                                    ↑
                              User (annotator_id)
```

| Tabla | Campos clave |
|-------|-------------|
| `users` | id, username, password_hash, role (`admin`/`annotator`) |
| `transcription_projects` | id, name, status, total_words, words_to_review |
| `segments` | id, project_id, audio_filename, text, text_revised, review_status, annotator_id, start_time, end_time |
| `words` | id, segment_id, word, word_index, probability, speaker, start_time, end_time |

---

## 🐳 Producción (Docker)

```bash
# 1. Configurar secretos
cp envs/web_app.env.example envs/web_app.env
python3 src/scripts/generate_secrets.py  # o manualmente:
python3 -c "import secrets; print(secrets.token_hex(64))"

# 2. Levantar servicios
docker compose -f docker-compose.prod.yml up -d

# 3. Verificar
docker compose -f docker-compose.prod.yml ps
curl -k https://localhost/login
```

Ver guías detalladas:
- [DEPLOYMENT_DOCKER_SETUP.md](DEPLOYMENT_DOCKER_SETUP.md) — Setup completo
- [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) — Checklist pre/post deploy
- [KEY_MANAGEMENT.md](KEY_MANAGEMENT.md) — Rotación de secretos
- [SECURITY.md](SECURITY.md) — Políticas de seguridad

---

## 🔧 Scripts útiles

| Script | Uso |
|--------|-----|
| `python init_and_import.py` | Reset BD + importar proyecto (¡destructivo!) |
| `python scripts/create_user.py <user> <pass> [role]` | Crear usuario |
| `python scripts/list_users.py` | Listar todos los usuarios |
| `python scripts/import_segments.py <project_id>` | Importar proyecto sin reset |
| `python scripts/assign_words.py` | Asignar segmentos pendientes |
| `python scripts/user_stats.py` | Ver estadísticas por usuario |

> Todos los scripts se ejecutan desde `src/`.

---

## 🔒 Seguridad

- Contraseñas hasheadas con Werkzeug (pbkdf2)
- JWT con expiración configurable
- Rate limiting (1000 req/hr por IP, admin exempt)
- CORS restringido en producción
- SSL/TLS vía Nginx
- **No** se incluyen secretos en el repo — generar antes de producción

---

## 📄 Licencia

Ver [LICENSE](src/LICENSE)</content>
<parameter name="filePath">/Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/README.md