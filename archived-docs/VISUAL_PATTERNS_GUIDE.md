# 🐳 GUÍA VISUAL: PATRONES DE DISEÑO + DOCKER

## 🎨 VISUALIZACIÓN INTERACTIVA

### EL VIAJE DE UN REQUEST DE USUARIO

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  👤 USUARIO EXTERNO                                            │
│  (En su laptop o celular)                                      │
│                                                                 │
│  {"Quiero descargar el audio de la palabra #42"}              │
│                                                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │  HTTPS Request
                     │  (vía Cloudflare Proxy)
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                       DOCKER HOST                              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                                                         │  │
│  │  🔒 CLOUDFLARE/NGINX Container                        │  │
│  │  Port: 443 (HTTPS) → 8080 (HTTP)                      │  │
│  │                                                         │  │
│  └────────────────────┬────────────────────────────────────┘  │
│                       │                                        │
│                       │  HTTP GET /api/v2/transcriptions/...  │
│                       │  Bearer: jwt_token                     │
│                       ↓                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ WEB_APP Container                                       │  │
│  │ (Flask Application)                                     │  │
│  │                                                         │  │
│  │ ┌─── BLUEPRINT PATTERN ─────────────────────────────┐ │  │
│  │ │                                                   │ │  │
│  │ │ Router receives:                                 │ │  │
│  │ │  GET /projects/memoria/words/42/audio           │ │  │
│  │ │                                                   │ │  │
│  │ │ Matches:                                         │ │  │
│  │ │  @transcription_bp.route(                        │ │  │
│  │ │    '/projects/<project_id>/words/<id>/audio'    │ │  │
│  │ │  )                                               │ │  │
│  │ │                                                   │ │  │
│  │ └───┬───────────────────────────────────────────────┘ │  │
│  │     │                                                 │  │
│  │     │                                                 │  │
│  │ ┌───┴─ DECORATOR PATTERN ──────────────────────────┐ │  │
│  │ │                                                   │ │  │
│  │ │ @jwt_required                                    │ │  │
│  │ │ ├─ Extract token from header                    │ │  │
│  │ │ ├─ Call: JWTService.verify_access_token(token)│ │  │
│  │ │ │  └─ Uses JWT_SECRET_KEY (from env_file)     │ │  │
│  │ │ ├─ Validate signature                          │ │  │
│  │ │ ├─ Extract: user_id, username, role           │ │  │
│  │ │ └─ Inject in request context                   │ │  │
│  │ │                                                   │ │  │
│  │ │ ✅ Token válido → Continúa                      │ │  │
│  │ │ ❌ Token inválido → 401 Unauthorized             │ │  │
│  │ │                                                   │ │  │
│  │ └───┬───────────────────────────────────────────────┘ │  │
│  │     │                                                 │  │
│  │ ┌───┴─ HANDLER (Controller) ────────────────────────┐ │  │
│  │ │                                                   │ │  │
│  │ │ def get_word_audio(project_id, word_id):        │ │  │
│  │ │                                                   │ │  │
│  │ │   # SINGLETON PATTERN (Dependency Injection)    │ │  │
│  │ │   db_manager = get_db_manager()                 │ │  │
│  │ │   audio_service = get_audio_service()           │ │  │
│  │ │                                                   │ │  │
│  │ └───┬───────────────────────────────────────────────┘ │  │
│  │     │                                                 │  │
│  │ ┌───┴─ SERVICE LAYER ───────────────────────────────┐ │  │
│  │ │                                                   │ │  │
│  │ │ # REPOSITORY PATTERN - Data Access              │ │  │
│  │ │ session = db_manager.get_session()             │ │  │
│  │ │ word = session.query(Word)                      │ │  │
│  │ │         .filter_by(id=42, project_id=memoria)  │ │  │
│  │ │         .first()                                │ │  │
│  │ │                                                   │ │  │
│  │ │ Result:                                          │ │  │
│  │ │ {                                                │ │  │
│  │ │   "id": 42,                                      │ │  │
│  │ │   "audio_filename": "audio_1.wav",              │ │  │
│  │ │   "word": "memoria",                            │ │  │
│  │ │   "start_time": 45.2,                           │ │  │
│  │ │   "end_time": 45.8,                             │ │  │
│  │ │   ...                                            │ │  │
│  │ │ }                                                │ │  │
│  │ │                                                   │ │  │
│  │ └───┬───────────────────────────────────────────────┘ │  │
│  │     │                                                 │  │
│  │ ┌───┴─ ADAPTER PATTERN (Audio Processing) ───────────┐ │  │
│  │ │                                                   │ │  │
│  │ │ audio_data = audio_service.extract_frame_segment(│ │  │
│  │ │   filepath="audio_1.wav",                       │ │  │
│  │ │   start_time=45.2 - 0.2,  # margin            │ │  │
│  │ │   end_time=45.8 + 0.2                          │ │  │
│  │ │ )                                                │ │  │
│  │ │                                                   │ │  │
│  │ │ # Internally (AudioService):                     │ │  │
│  │ │ # ├─ Uses librosa (via try-except)             │ │  │
│  │ │ # ├─ Loads audio file                          │ │  │
│  │ │ # ├─ Extracts frames                           │ │  │
│  │ │ # ├─ Converts to WAV                           │ │  │
│  │ │ # └─ Returns bytes                             │ │  │
│  │ │                                                   │ │  │
│  │ │ # Encapsulation complete - AudioService        │ │  │
│  │ │ # hides complexity of librosa                  │ │  │
│  │ │                                                   │ │  │
│  │ └───┬───────────────────────────────────────────────┘ │  │
│  │     │                                                 │  │
│  │ ┌───┴─ RESPONSE ────────────────────────────────────┐ │  │
│  │ │                                                   │ │  │
│  │ │ return send_file(                                │ │  │
│  │ │   BytesIO(audio_bytes),                         │ │  │
│  │ │   mimetype='audio/wav'                          │ │  │
│  │ │ )                                                │ │  │
│  │ │                                                   │ │  │
│  │ │ HTTP/1.1 200 OK                                 │ │  │
│  │ │ Content-Type: audio/wav                         │ │  │
│  │ │ Content-Length: 45632                           │ │  │
│  │ │ [WAV audio stream...]                           │ │  │
│  │ │                                                   │ │  │
│  │ └───────────────────────────────────────────────────┘ │  │
│  │                                                         │  │
│  └────────────────────┬────────────────────────────────────┘  │
│                       │                                        │
│                       │ HTTP Response (WAV file)               │
│                       ↓                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ 🔒 CLOUDFLARE/NGINX Container                        │  │
│  │ Port: 8080 (HTTP) → 443 (HTTPS)                      │  │
│  │                                                         │  │
│  └────────────────────┬────────────────────────────────────┘  │
│                       │                                        │
│                       │ HTTPS Response                         │
│                       ↓                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                     │
                     │
                     ↓
        ┌─────────────────────────────┐
        │ 👤 USUARIO EXTERNO          │
        │ Recibe el audio de "memoria"│
        │ ¡Reproducible en su app!    │
        └─────────────────────────────┘
```

---

## 🔄 LOS 8 PATRONES EN ACCIÓN

### 1️⃣ FACTORY PATTERN
```python
# app.py
def create_app():
    """Factory que crea instancia de Flask lista para operar"""
    app = Flask(__name__)
    config = Config.from_env()  # Lee secrets del env
    db_manager = DatabaseManager(config.DATABASE_URL)
    db_manager.create_tables()
    # ... retorna app completamente configurada
    return app
```

**Ventaja en Docker:**  
Cada contenedor que ejecuta `create_app()` obtiene su propia instancia con la configuración correcta.

---

### 2️⃣ SERVICE LAYER PATTERN
```
┌─────────────────────────────────────┐
│ Servicios (Services/)               │
├─────────────────────────────────────┤
│                                     │
│ JWTService                          │
│  ├─ create_access_token()           │
│  ├─ verify_access_token()           │
│  └─ generate_secret() [fallback]    │
│                                     │
│ TranscriptionService                │
│  ├─ parse_words_from_transcript()   │
│  ├─ import_transcript_to_db()       │
│  └─ get_project_stats()             │
│                                     │
│ AudioService                        │
│  ├─ extract_frame_segment()         │
│  └─ get_project_path()              │
│                                     │
│ HealthChecker                       │
│  ├─ check_database_health()         │
│  ├─ check_disk/memory/cpu_health()  │
│  └─ perform_full_health_check()     │
│                                     │
└─────────────────────────────────────┘
```

**Ventaja:**  
- Cada servicio tiene UNA responsabilidad
- Separación clara = Fácil de testear
- Cambios localizados a un servicio

---

### 3️⃣ REPOSITORY PATTERN

```
┌────────────────────────────────────────┐
│ DatabaseManager (Repository)           │
├────────────────────────────────────────┤
│                                        │
│  get_session()                         │
│    └─ Devuelve sesión SQLAlchemy      │
│                                        │
│  create_tables()                       │
│    └─ Crea todas las tablas           │
│                                        │
│  Encapsula:                            │
│    ├─ SQLite en desarrollo            │
│    ├─ PostgreSQL en producción        │
│    └─ Cambios sin tocar código        │
│                                        │
│ ORM Models:                            │
│    ├─ User                            │
│    ├─ TranscriptionProject            │
│    └─ Word (con índices optimizados)  │
│                                        │
└────────────────────────────────────────┘
```

**Ventaja en Docker:**  
La URL de BD se inyecta via `DATABASE_URL` env var.  
Mismo código funciona con SQLite o PostgreSQL.

---

### 4️⃣ BLUEPRINT PATTERN

```
┌────────────────────────────────────────┐
│ Flask Blueprints (routes/)             │
├────────────────────────────────────────┤
│                                        │
│ transcription_bp (url_prefix='/api/v2')
│                                        │
│ GET    /projects                      │
│ GET    /projects/<id>                │
│ GET    /projects/<id>/words           │
│ GET    /projects/<id>/words/<id>/audio
│ POST   /words/<id> [submit_correction]|
│ POST   /projects [admin_required]     │
│ POST   /projects/<id>/import [admin]  │
│ POST   /words/<id>/assign [admin]     │
│                                        │
│ Beneficio:                             │
│ └─ Prefijo centralizado               │
│ └─ Fácil de versionar (/api/v3)      │
│ └─ Escalable horizontalmente          │
│                                        │
└────────────────────────────────────────┘
```

---

### 5️⃣ DECORATOR PATTERN

```
┌────────────────────────────────────────┐
│ Cross-Cutting Concerns                 │
├────────────────────────────────────────┤
│                                        │
│ @jwt_required                         │
│   ├─ Valida JWT token                 │
│   ├─ Obtiene user_id del token        │
│   └─ Inyecta en request context        │
│                                        │
│ @admin_required                        │
│   ├─ Verifica rol='admin'              │
│   └─ Retorna 403 si no es admin       │
│                                        │
│ @rate_limit                            │
│   ├─ Limita N requests por IP         │
│   └─ Retorna 429 si exceed            │
│                                        │
│ Composición:                           │
│ @transcription_bp.route(...)           │
│ @jwt_required  ←─ 1er decorador       │
│ @admin_required ←─ 2do decorador      │
│ def handler():  ←─ Ejecuta solo si OK │
│                                        │
└────────────────────────────────────────┘
```

---

### 6️⃣ CONFIGURATION OBJECT PATTERN

```
┌────────────────────────────────────────┐
│ config.py                              │
├────────────────────────────────────────┤
│                                        │
│ @dataclass                             │
│ class Config:                          │
│     FLASK_ENV: str                    │
│     JWT_SECRET_KEY: str [Required]    │
│     SECRET_KEY: str [Required]        │
│     DATABASE_URL: str                 │
│     WORKERS: int                      │
│     LOG_LEVEL: str                    │
│     ... 20+ más parámetros            │
│                                        │
│ @classmethod                           │
│ def from_env(cls):                     │
│     """Lee TODAS las vars de entorno"""|
│     return cls(...)                   │
│                                        │
│ def validate_production_config():      │
│     """Valida en producción"""         │
│     if JWT_SECRET_KEY < 32 chars:     │
│         raise ValueError()             │
│                                        │
│ ┌────────────────────────────────────┤
│ │ En Docker:                         │
│ │ docker-compose.yml:                │
│ │   env_file: ./envs/web_app.env     │
│ │   └─ Inyecta variables             │
│ │                                    │
│ │ Config.from_env() las lee          │
│ │ Valida automáticamente             │
│ │ Retorna configuración lista        │
│ └────────────────────────────────────┘
│                                        │
└────────────────────────────────────────┘
```

---

### 7️⃣ ADAPTER PATTERN

```
┌────────────────────────────────────────┐
│ AudioService (Adapter)                 │
├────────────────────────────────────────┤
│                                        │
│ Interfaz Externa:                      │
│ def extract_frame_segment(             │
│     filepath, start_time, end_time     │
│ )                                      │
│                                        │
│ Internamente (Encapsulado):            │
│ ├─ try:                               │
│ │   import librosa                    │
│ │   import soundfile as sf            │
│ │   import numpy as np                │
│ │ except ImportError:                 │
│ │   LIBROSA_AVAILABLE = False         │
│ │                                     │
│ │ y, sr = librosa.load(filepath)     │
│ │ [extrae segmento]                   │
│ │ sf.write(buffer, y, sr)            │
│ │ return buffer.getvalue()            │
│ │                                     │
│ └─ Cliente NO sabe/importa librosa  │
│                                        │
│ Beneficio:                             │
│ Cambiar librosa → scipy               │
│ SOLO modificas AudioService           │
│ El resto de la app no se entera       │
│                                        │
└────────────────────────────────────────┘
```

---

### 8️⃣ SINGLETON PATTERN

```python
# services/jwt_service.py
jwt_service = JWTService()  # Una sola instancia

# Uso en toda la app:
from services.jwt_service import jwt_service

# Siempre es la MISMA instancia
# No reinicializa en cada request
# Eficiente: config cargada una vez
```

**Ventaja:**  
- Memoria eficiente
- Consistencia global
- Rápido acceso

---

## 🐳 DOCKER COMPOSE - EL ORQUESTADOR

```yaml
version: '3.8'

services:
  # 1. Proxy inverso HTTPS
  cloudflare:
    container_name: cloudflare
    ports:
      - "443:443"  # HTTPS
    depends_on:
      - web_app

  # 2. Aplicación Flask (todos los patrones)
  web_app:
    container_name: web_app
    build: docker/web_app/
    env_file: ./envs/web_app.env  # ← Variables de config
    depends_on:
      postgres:
        condition: service_healthy  # ← Espera a que DB inicie
    ports:
      - "8080:8080"
    volumes:
      - ./src:/app  # Hot reload en desarrollo

  # 3. Base de datos PostgreSQL
  postgres:
    container_name: postgres
    image: postgres:15
    env_file: ./envs/postgres.env
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 10s
      retries: 5
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:  # Persistencia de datos
```

---

## ✨ SUMMARY: PATRONES + DOCKER = ARQUITECTURA PERFECTA

| Elemento | Qué Hace | Por Qué Importa |
|----------|----------|-----------------|
| **Factory** | Crea app controlada | Consistencia en todos lados |
| **Services** | Lógica separada | Escalable, mantenible |
| **Repository** | BD agnóstica | Cambiar BD sin changesets |
| **Blueprint** | Rutas modulares | Agregar features fácil |
| **Decorators** | Cross-cutting | Código limpio |
| **Config** | Secrets vía env | Seguro en producción |
| **Adapter** | Encapsula librerías | Cambios sin impact |
| **Singleton** | Una instancia | Memoria eficiente |
| **Docker** | Orquesta todo | Reproducible, escalable |

**Resultado:** Un sistema que es:
- ✅ Escalable horizontalmente
- ✅ Fácil de mantener
- ✅ Seguro en producción
- ✅ Deployable en cualquier servidor
- ✅ Testeable automáticamente
