# 🏛️ ARQUITECTURA DE PATRONES DE DISEÑO INTEGRADA CON DOCKER

## 📊 DIAGRAMA COMPLETO DEL FLUJO DE INFORMACIÓN

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│                    INTERNET / CLIENT APPLICATION                  │
│                                                                    │
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 │ HTTP/HTTPS Request
                 ↓
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  ┌──────────────────────┐                                         │
│  │   DOCKER CONTAINER   │                                         │
│  │    (web_app)         │                                         │
│  │                      │                                         │
│  └──────────────────────┘                                         │
│           ↓                                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  FLASK APPLICATION (app.py)                               │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │ PATTERN #1: FACTORY PATTERN                         │ │  │
│  │  │ create_app() → Configures Flask instance            │ │  │
│  │  │ Injects: Config, Services, Blueprints               │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │           ↓                                                │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │ PATTERN #2: BLUEPRINT PATTERN (routes/)              │ │  │
│  │  │                                                       │ │  │
│  │  │  transcription_bp.route('/projects/<id>/words/<id>') │ │  │
│  │  │  GET (/api/v2/transcriptions/...)                   │ │  │
│  │  │  POST (/api/v2/transcriptions/...) [admin only]    │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  │           ↓                                                │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │ PATTERN #3: DECORATOR PATTERN                        │ │  │
│  │  │                                                       │ │  │
│  │  │  @jwt_required        ← JWT Service validates token │ │  │
│  │  │  @admin_required      ← Checks user role           │ │  │
│  │  │  @rate_limit          ← Limits requests per IP      │ │  │
│  │  │                                                       │ │  │
│  │  │ Decorators intercept request → Validate → Continue  │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  │           ↓                                                │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │ PATTERN #4: SERVICE LAYER PATTERN (services/)        │ │  │
│  │  │                                                       │ │  │
│  │  │  ┌─────────────────────────────────────────────┐    │ │  │
│  │  │  │ JWTService                                  │    │ │  │
│  │  │  │ - create_access_token()                     │    │ │  │
│  │  │  │ - verify_access_token()                     │    │ │  │
│  │  │  │ - create_refresh_token()                    │    │ │  │
│  │  │  └─────────────────────────────────────────────┘    │ │  │
│  │  │                                                       │ │  │
│  │  │  ┌─────────────────────────────────────────────┐    │ │  │
│  │  │  │ TranscriptionService                        │    │ │  │
│  │  │  │ - parse_words_from_transcript()             │    │ │  │
│  │  │  │ - import_transcript_to_db()                 │    │ │  │
│  │  │  │ - get_project_stats()                       │    │ │  │
│  │  │  └─────────────────────────────────────────────┘    │ │  │
│  │  │                                                       │ │  │
│  │  │  ┌─────────────────────────────────────────────┐    │ │  │
│  │  │  │ AudioService (ADAPTER PATTERN)              │    │ │  │
│  │  │  │ - extract_frame_segment()                   │    │ │  │
│  │  │  │   ↓ (Encapsulates librosa + soundfile)     │    │ │  │
│  │  │  └─────────────────────────────────────────────┘    │ │  │
│  │  │                                                       │ │  │
│  │  │  ┌─────────────────────────────────────────────┐    │ │  │
│  │  │  │ HealthChecker & NotificationService        │    │ │  │
│  │  │  │ - check_database_health()                   │    │ │  │
│  │  │  │ - check_disk/memory/cpu_health()            │    │ │  │
│  │  │  │ - send_admin_notification()                 │    │ │  │
│  │  │  └─────────────────────────────────────────────┘    │ │  │
│  │  │                                                       │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  │           ↓                                                │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │ PATTERN #5: CONFIGURATION OBJECT (config.py)         │ │  │
│  │  │                                                       │ │  │
│  │  │ Config.from_env()                                    │ │  │
│  │  │  ↓                                                   │ │  │
│  │  │ Reads from Docker env_file:                         │ │  │
│  │  │  - jwt_secret_key (injected via secrets)           │ │  │
│  │  │  - database_url (points to postgres container)     │ │  │
│  │  │  - log_level, workers, etc.                        │ │  │
│  │  │                                                       │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  │           ↓                                                │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │ PATTERN #6: REPOSITORY/DAO PATTERN (models/)         │ │  │
│  │  │                                                       │ │  │
│  │  │ DatabaseManager                                      │ │  │
│  │  │  ├─ get_session()                                   │ │  │
│  │  │  └─ create_tables()                                 │ │  │
│  │  │                                                       │ │  │
│  │  │ ORM Models (SQLAlchemy):                            │ │  │
│  │  │  ├─ User          (id, username, role, ...)        │ │  │
│  │  │  ├─ TranscriptionProject (id, name, status, ...)  │ │  │
│  │  │  └─ Word          (id, project_id, word, prob...)  │ │  │
│  │  │                                                       │ │  │
│  │  │ ┌──────────────────────────────────────────────┐   │ │  │
│  │  │ │ Relaciones:                                  │   │ │  │
│  │  │ │  User ──(1:N)──> Word                       │   │ │  │
│  │  │ │  Project ──(1:N)──> Word                    │   │ │  │
│  │  │ │                                              │   │ │  │
│  │  │ │ Índices:                                    │   │ │  │
│  │  │ │  - idx_word_project_status                 │   │ │  │
│  │  │ │  - idx_word_annotator_status               │   │ │  │
│  │  │ │  - idx_word_probability                    │   │ │  │
│  │  │ └──────────────────────────────────────────────┘   │ │  │
│  │  │                                                       │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────┘  │
│           ↓                                                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ DOCKER NETWORK (bridge network)                          │  │
│  │ Comunica entre contenedores por nombre de servicio       │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────────────────────────────────┐
│                         DOCKER CONTAINERS                         │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ postgres:15 (Servicio de BD)                           │    │
│  │                                                         │    │
│  │ DATABASE_URL = postgresql://postgres:5432/db          │    │
│  │ (Accesible como "postgres" dentro de Docker network)  │    │
│  │                                                         │    │
│  │ ┌─────────────────────────────────────────────────┐   │    │
│  │ │ Tablas Persistentes:                            │   │    │
│  │ │  - users                                        │   │    │
│  │ │  - transcription_projects                       │   │    │
│  │ │  - words                                        │   │    │
│  │ │                                                 │   │    │
│  │ │ Health Check (Docker):                          │   │    │
│  │ │  pg_isready -U postgres                         │   │    │
│  │ │  → web_app solo inicia si DB está lista        │   │    │
│  │ │                                                 │   │    │
│  │ └─────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ cloudflare/nginx (Proxy inverso HTTPS)                │    │
│  │                                                         │    │
│  │ 443 (HTTPS) → 8080 (HTTP web_app)                     │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 FLUJO DE UNA SOLICITUD COMPLETO

### 1️⃣ REQUEST: Usuario descarga audio de una palabra

```http
GET /api/v2/transcriptions/projects/memoria_1970/words/42/audio
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

### 2️⃣ BLUEPRINT PATTERN
```
Flask URL Routing (Blueprint)
├─ URL: /api/v2/transcriptions/projects/<id>/words/<id>/audio
├─ Method: GET
├─ Handler: get_word_audio(project_id, word_id)
└─ Prefijo automaticamente añadido: /api/v2/transcriptions
```

---

### 3️⃣ DECORATOR PATTERN (Middleware)
```
@jwt_required (Decorador #1)
│
├─ Extrae token del header Authorization
├─ JWTService.verify_access_token(token)
│  └─ Verifica signature con JWT_SECRET_KEY
│  └─ Obtiene payload: {user_id, username, role}
├─ Inyecta en request context
└─ Continúa si token válido

→ Si falla: return 401 Unauthorized
```

---

### 4️⃣ SERVICE LAYER (Lógica de Negocio)
```
def get_word_audio(project_id, word_id):
    # Inyección de dependencias (PATTERN: Singleton)
    db_manager = get_db_manager()
    audio_service = get_audio_service()
    
    # REPOSITORY PATTERN: Acceso a datos
    session = db_manager.get_session()
    word = session.query(Word)\
        .filter_by(id=word_id, project_id=project_id)\
        .first()
    
    # ADAPTER PATTERN: Audio Service encapsula librosa
    audio_data = audio_service.extract_frame_segment(
        filepath=word.audio_filename,
        start_time=word.start_time - 0.2,  # margin
        end_time=word.end_time + 0.2
    )
    
    # AudioService internamente:
    #  ├─ Usa librosa (via try-except si disponible)
    #  ├─ Extrae frames
    #  ├─ Convierte a WAV
    #  └─ Retorna bytes
    
    return send_file(BytesIO(audio_data), mimetype='audio/wav')
```

---

### 5️⃣ CONFIGURATION PATTERN (Variables de Entorno)
```
┌─────────────────────────────────────────────────────┐
│ docker-compose.yml                                  │
│                                                     │
│ services:                                           │
│   web_app:                                          │
│     env_file: ./envs/web_app.env        ←─┐         │
│     environment:                           │        │
│       DATABASE_URL: postgresql://...      │        │
│                                            │        │
└─────────────────────────────────────────────────────┘
                                             │
                                             ↓
┌─────────────────────────────────────────────────────┐
│ config.py                                           │
│                                                     │
│ @dataclass                                          │
│ class Config:                                       │
│     JWT_SECRET_KEY: str                            │
│     DATABASE_URL: str                              │
│     ...                                            │
│                                                     │
│     @classmethod                                    │
│     def from_env(cls):                              │
│         return cls(                                 │
│             JWT_SECRET_KEY=os.getenv('...'),       │
│             DATABASE_URL=os.getenv('...'),         │
│             ...                                    │
│         )                                          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🐳 CÓMO DOCKER OPTIMIZA LOS PATRONES

### 1. Factory Pattern + Docker
```
┌──────────────────────────────────────────┐
│ Dockerfile                               │
│                                          │
│ FROM python:3.10-slim                   │
│ COPY requirements.txt .                 │
│ RUN pip install -r requirements.txt     │
│                                          │
│ CMD ["python", "app.py"]                │
│    └─ Ejecuta create_app()              │
│                                          │
└──────────────────────────────────────────┘
        ↓
Cada contenedor ejecuta create_app()
con su propia configuración
```

### 2. Service Layer + Docker Container
```
┌──────────────────────────────────────┐
│ services:                            │
│   web_app:                           │
│     build: docker/web_app            │
│     depends_on:                      │
│       postgres:                      │
│         condition: service_healthy   │
│                                      │
└──────────────────────────────────────┘
        ↓
- Cada servicio es un contenedor
- TranscriptionService, JWTService corren aquí
- Escalable: replicas: 3 para múltiples instancias
```

### 3. Repository Pattern + Docker Network
```
┌────────────────────────────────────────┐
│ config.DATABASE_URL =                │
│ "postgresql://postgres:5432/db"      │
│                                       │
│ Dentro del Docker network:            │
│  "postgres" → resuelve a la IP        │
│              del contenedor postgres  │
│                                       │
│ DatabaseManager se conecta            │
│ automáticamente al db correcto        │
│                                       │
└────────────────────────────────────────┘
```

### 4. Health Checks + Docker Orchestration
```
postgres:
  healthcheck:
    test: ["CMD", "pg_isready", "-U", "postgres"]
    interval: 10s
    timeout: 5s
    retries: 5

web_app:
  depends_on:
    postgres:
      condition: service_healthy  ←─ Solo inicia cuando DB está lista

HealthChecker Python (services/health_service.py):
  perform_full_health_check()
  └─ Verifica DB (usando healthcheck de Docker)
  └─ Verifica disco/memoria/CPU
  └─ Envía alertas si hay problemas
```

---

## ✅ OPTIMIZACIONES IMPLEMENTADAS Y PENDIENTES

### 🟢 IMPLEMENTADAS
- ✅ **Factory Pattern** → create_app() centralizada
- ✅ **Service Layer** → Lógica separada por responsabilidad
- ✅ **Repository Pattern** → Acceso a datos centralizado
- ✅ **Blueprint Pattern** → Rutas modulares por función
- ✅ **Decorator Pattern** → Cross-cutting concerns (JWT, rate-limit)
- ✅ **Configuration Object** → Secrets management robusto
- ✅ **Adapter Pattern** → Audio processing encapsulado
- ✅ **Singleton Pattern** → Instancias globales de servicios
- ✅ **Docker Compose** → Multi-container orchestration
- ✅ **Health Checks** → Docker + Python integration
- ✅ **Dependency Injection** → Via funciones get_*()

### 🟡 RECOMENDACIONES PARA OPTIMIZAR AÚN MÁS

#### 1. **Inyección de Dependencias Mejorada**
```python
# ACTUAL (Manual)
def list_projects():
    db_manager = get_db_manager()
    session = db_manager.get_session()

# RECOMENDADO (Framework di)
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    db_manager = providers.Singleton(DatabaseManager, config)
    jwt_service = providers.Singleton(JWTService, config)

# Uso:
@transcription_bp.route('/projects')
def list_projects(db_manager: DatabaseManager = Depends()):
    pass
```

#### 2. **Multi-stage Docker Build**
```dockerfile
# Stage 1: Builder
FROM python:3.10-slim as builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime (imagen 50% más pequeña)
FROM python:3.10-slim
COPY --from=builder /root/.local /root/.local
COPY src /app
WORKDIR /app
CMD ["python", "app.py"]
```

#### 3. **Resource Limits en Docker**
```yaml
web_app:
  resources:
    limits:
      cpus: '2'
      memory: 1024M
    reservations:
      cpus: '0.5'
      memory: 256M

postgres:
  resources:
    limits:
      cpus: '4'
      memory: 2048M
```

#### 4. **Logging Centralizado**
```yaml
services:
  web_app:
    logging:
      driver: "splunk"  # o ELK stack, Datadog, etc
      options:
        splunk-token: "xxx"
        splunk-url: "https://xxx"
```

---

## 📊 TABLA COMPARATIVA: Patrones y su Impacto

| Patrón | Beneficio | Impacto |  Docker |
|--------|-----------|--------|--------|
| **Factory** | Instancias controladas | Inicialización centralizada | Cada contenedor su app |
| **Service Layer** | SRP + Reutilización | Código limpio y testeable | Servicios escalables |
| **Repository** | Abstracción BD | BD agnóstica | Multi-BD compatible |
| **Blueprint** | Modularidad | Fácil agregar features | Escalabilidad de rutas |
| **Decorator** | Cross-cutting | Código limpio | Middleware eficiente |
| **Configuration** | Flexibilidad | Env-driven | Multi-entorno |
| **Adapter** | Desacoplamiento | Cambios de librería fácil | Dependencias flexibles |
| **Singleton** | Eficiencia | Una instancia/servicio | Consistencia en contenedor |

---

## 🎯 RESUMEN: ¿POR QUÉ ESTOS PATRONES SON ÓPTIMOS?

1. **Escalabilidad**: Agregar nuevas funcionalidades sin modificar código existente
2. **Mantenibilidad**: Cambios localizados a un servicio/módulo
3. **Testabilidad**: Mock fácil de dependencias
4. **Performance**: Indexación BD, caching con Singleton
5. **Robustez**: Validación automática, health checks
6. **Seguridad**: JWT separado, secrets management centralizado
7. **Devops**: Docker compose coordina todo el stack
8. **Observabilidad**: Logging e health checks integrados
