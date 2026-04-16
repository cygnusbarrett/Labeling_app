# 🎵 Módulo de Validación de Transcripciones de Audio

Extensión del repositorio de anotación colaborativa que permite validar transcripciones de audio (conversiones de voz a texto) mediante un enfoque similar al del módulo de OCR, pero adaptado para audios.

## 📋 Resumen Técnico

### Objetivo
Permitir que **anotadores** validen transcripciones de audio de baja confianza (probability < 0.95), escuchando extractos de audio y confirmando o corrigiendo la transcripción.

### Características Principales
- ✅ Carga de proyectos con múltiples audios
- ✅ Parseo automático de JSONs de transcripción
- ✅ Filtrado inteligente de palabras por probability
- ✅ Recorte de audio on-demand con margen configurable
- ✅ Dashboard diferenciado para admin vs anotadores
- ✅ Estadísticas en tiempo real por proyecto y anotador
- ✅ Asignación flexible de palabras a anotadores
- ✅ Historial de correcciones

---

## 🏗️ Arquitectura

### Estructura de Carpetas
```
src/
├── data/
│   └── transcription_projects/
│       └── memoria_1970_1990/              # Proyecto único
│           ├── D 394 caja 6 cinta 1 Osvaldo Muray lado B-01_short_full.wav
│           ├── D 394 caja 6 cinta 1 Osvaldo Muray lado B-01_short_full.json
│           ├── [audio_002.wav]
│           ├── [audio_002.json]
│           └── metadata.json               # Descripción del proyecto
│
├── models/
│   └── database.py                        # Nuevas: Word, TranscriptionProject
│
├── services/
│   ├── audio_service.py                   # Recorte on-demand de audio
│   └── transcription_service.py           # Parseo y validación de JSONs
│
├── routes/
│   └── transcription_api_routes.py        # API endpoints
│
└── scripts/
    └── load_transcription_project.py      # Script para cargar primer audio
```

### Modelos de Base de Datos

#### `TranscriptionProject`
Representa un proyecto de transcripción
```
id: "memoria_1970_1990"
name: "Archivo de Audio - Memoria 1970-1990"
description: "..."
total_words: 5000
words_to_review: 250
words_completed: 45
status: "active" | "completed" | "archived"
created_at, updated_at, completed_at
```

#### `Word`
Representa una palabra individual en una transcripción
```
id: 1
project_id: "memoria_1970_1990"
audio_filename: "D 394 caja 6 cinta 1 Osvaldo Muray lado B-01_short_full.wav"
word_index: 42
word: "transcrito"
speaker: "SPEAKER_01"
probability: 0.8765
start_time: 123.45
end_time: 124.12
alignment_score: 0.492
status: "pending" | "approved" | "corrected"
annotator_id: 2
corrected_text: "transcribió"
created_at, updated_at, completed_at
```

---

## 🚀 Guía de Uso

### 1️⃣ Instalación de Dependencias

```bash
cd src/
pip install -r requirements/requirements.txt
```

**Nuevas dependencias agregadas:**
- `librosa==0.10.0` - Procesamiento de audio
- `soundfile==0.12.1` - Lectura/escritura de WAV
- `numpy==1.24.3` - Álgebra lineal

### 2️⃣ Preparar Archivos de Audio

**Estructura esperada** (copia tus archivos aquí):
```
src/data/transcription_projects/memoria_1970_1990/
├── D 394 caja 6 cinta 1 Osvaldo Muray lado B-01_short_full.wav
├── D 394 caja 6 cinta 1 Osvaldo Muray lado B-01_short_full.json
└── metadata.json
```

**Nota:** Los nombres de archivos .wav y .json deben coincidir exactamente (menos la extensión)

### 3️⃣ Cargar Transcripción en BD

```bash
cd src/
python scripts/load_transcription_project.py
```

**Salida esperada:**
```
======================================================================
SCRIPT DE CARGA: Transcripción de Audio Osvaldo Muray
======================================================================

📁 Proyecto: memoria_1970_1990
📝 Nombre: Archivo de Audio - Memoria 1970-1990
🎵 Audio: D 394 caja 6 cinta 1 Osvaldo Muray lado B-01_short_full.wav
📄 Transcripción: D 394 caja 6 cinta 1 Osvaldo Muray lado B-01_short_full.json

⏳ Creando proyecto...
✅ Proyecto creado: memoria_1970_1990

⏳ Importando transcripción...
✅ 250 palabras importadas

📊 Estadísticas del Proyecto:
   - Total de palabras: 5000
   - Palabras a revisar (prob < 0.95): 250
   - Palabras completadas: 0
   - Estado: active

📋 Primeras 5 palabras para revisar:
   1. [SPEAKER_01] 'el' (prob: 0.342)
      Tiempo: 0.00s - 0.20s
   2. [SPEAKER_01] 'vocero' (prob: 0.857)
      Tiempo: 13.78s - 14.12s
   ...
```

### 4️⃣ Iniciar la Aplicación

```bash
python app.py
```

Abre: `http://localhost:8080`

---

## 📡 API REST Endpoints

### Autenticación
Todos los endpoints requieren JWT token en header:
```
Authorization: Bearer <token>
```

### Proyectos

#### `GET /api/v2/transcriptions/projects`
Lista todos los proyectos
```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8080/api/v2/transcriptions/projects
```

**Response:**
```json
{
  "projects": [
    {
      "id": "memoria_1970_1990",
      "name": "Archivo de Audio - Memoria 1970-1990",
      "total_words": 5000,
      "words_to_review": 250,
      "words_completed": 45,
      "progress": 18.0,
      "status": "active"
    }
  ]
}
```

#### `GET /api/v2/transcriptions/projects/<project_id>`
Obtiene detalles de un proyecto
```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8080/api/v2/transcriptions/projects/memoria_1970_1990
```

### Palabras

#### `GET /api/v2/transcriptions/projects/<project_id>/words`
Lista palabras de un proyecto
```bash
# Filtrar por status
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8080/api/v2/transcriptions/projects/memoria_1970_1990/words?status=pending&limit=10&offset=0"
```

**Query params:**
- `status`: "pending", "approved", "corrected" (opcional)
- `limit`: 1-100 (default 50)
- `offset`: para paginación

**Response:**
```json
{
  "total": 250,
  "limit": 10,
  "offset": 0,
  "words": [
    {
      "id": 1,
      "word": "el",
      "speaker": "SPEAKER_01",
      "probability": 0.342,
      "start_time": 0.0,
      "end_time": 0.2,
      "status": "pending",
      "annotator_id": null
    }
  ]
}
```

#### `GET /api/v2/transcriptions/projects/<project_id>/words/<word_id>/audio`
Obtiene el audio de una palabra (bytes WAV)
```bash
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8080/api/v2/transcriptions/projects/memoria_1970_1990/words/1/audio?margin=0.2" \
  -o word_1.wav
```

**Query params:**
- `margin`: segundos a agregar antes/después (default 0.2)

### Anotación

#### `POST /api/v2/transcriptions/words/<word_id>`
Envía la corrección/validación de una palabra

```bash
curl -X POST \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "memoria_1970_1990",
    "status": "corrected",
    "corrected_text": "transcribió"
  }' \
  http://localhost:8080/api/v2/transcriptions/words/1
```

**Body:**
```json
{
  "project_id": "string",
  "status": "approved" | "corrected",
  "corrected_text": "string (required si status='corrected')"
}
```

**Response:**
```json
{
  "message": "Corrección guardada",
  "word": {
    "id": 1,
    "status": "corrected",
    "corrected_text": "transcribió",
    "completed_at": "2026-01-28T10:30:00"
  },
  "project_stats": {
    "words_completed": 46,
    "progress": 18.4
  }
}
```

### Estadísticas

#### `GET /api/v2/transcriptions/projects/<project_id>/stats`
Obtiene estadísticas del proyecto

```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8080/api/v2/transcriptions/projects/memoria_1970_1990/stats
```

**Response (Admin):**
```json
{
  "project": {
    "id": "memoria_1970_1990",
    "words_completed": 46,
    "progress": 18.4
  },
  "by_annotator": [
    {
      "annotator_username": "juan",
      "annotator_id": 2,
      "completed": 23,
      "approved": 20,
      "corrected": 3,
      "progress": 9.2
    },
    {
      "annotator_username": "maria",
      "annotator_id": 3,
      "completed": 23,
      "progress": 9.2
    }
  ]
}
```

**Response (Anotador):**
```json
{
  "project": {...},
  "my_stats": {
    "total_words": 125,
    "completed": 23,
    "pending": 102,
    "progress": 18.4
  }
}
```

### Admin - Gestión

#### `POST /api/v2/transcriptions/projects` (Admin)
Crea un nuevo proyecto

```bash
curl -X POST \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "memoria_1970_1990",
    "name": "Archivo de Audio - Memoria 1970-1990",
    "description": "..."
  }' \
  http://localhost:8080/api/v2/transcriptions/projects
```

#### `POST /api/v2/transcriptions/projects/<project_id>/import` (Admin)
Importa transcripción desde archivo JSON

```bash
curl -X POST \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_filename": "D 394 caja 6 cinta 1 Osvaldo Muray lado B-01_short_full.wav",
    "transcript_filename": "D 394 caja 6 cinta 1 Osvaldo Muray lado B-01_short_full.json",
    "probability_threshold": 0.95,
    "assign_to_annotators": [2, 3, 4]
  }' \
  http://localhost:8080/api/v2/transcriptions/projects/memoria_1970_1990/import
```

#### `POST /api/v2/transcriptions/projects/<project_id>/words/<word_id>/assign` (Admin)
Asigna una palabra a un anotador

```bash
curl -X POST \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"annotator_id": 2}' \
  http://localhost:8080/api/v2/transcriptions/projects/memoria_1970_1990/words/1/assign
```

---

## 🔒 Control de Acceso (Roles)

### Admin
- ✅ Ver todos los proyectos y palabras
- ✅ Ver estadísticas globales y por anotador
- ✅ Crear/actualizar proyectos
- ✅ Importar transcripciones
- ✅ Asignar palabras a anotadores
- ✅ Anotar cualquier palabra

### Anotador
- ✅ Ver solo sus palabras asignadas
- ✅ Ver solo sus estadísticas
- ❌ No puede crear proyectos
- ❌ No puede asignar palabras
- ✅ Anotar sus palabras asignadas

---

## 📊 Flujo de Trabajo Típico

```
1. ADMIN: Sube archivo .wav y .json
   └─> POST /api/v2/transcriptions/projects/
       POST /api/v2/transcriptions/projects/{id}/import

2. ADMIN: Asigna palabras a anotadores
   └─> POST /api/v2/transcriptions/projects/{id}/words/{id}/assign

3. ANOTADOR: Accede a /transcription/validator
   ├─> GET /api/v2/transcriptions/projects/{id}/words?status=pending
   ├─> GET /api/v2/transcriptions/projects/{id}/words/{id}/audio
   └─> POST /api/v2/transcriptions/words/{id}

4. ADMIN: Revisa estadísticas
   └─> GET /api/v2/transcriptions/projects/{id}/stats

5. Repetir pasos 3-4 hasta completar todas las palabras
```

---

## 🔧 Configuración Avanzada

### Umbral de Probability (metadata.json)
Por defecto se cargan palabras con `probability < 0.95`

Para cambiar:
```bash
# Editar antes de cargar
python scripts/load_transcription_project.py  # Usa 0.95 hardcoded

# Alternativa: pasar parámetro
# (Requiere modificación del script)
```

### Caché de Audio
El servicio `audio_service` mantiene audios en RAM para evitar releer archivos.

Para limpiar caché:
```python
from services.audio_service import audio_service
audio_service.clear_cache(project_id="memoria_1970_1990")  # Proyecto
audio_service.clear_cache()  # Todo
```

### Sample Rate
Por defecto: **16000 Hz (16 kHz)**

Para cambiar en recortes:
```
GET /api/v2/transcriptions/.../audio?sr=44100
```

---

## 📝 Formato Esperado del JSON de Transcripción

```json
{
  "words": [
    {
      "word": "el",
      "start": 0.0,
      "end": 0.2,
      "speaker": "SPEAKER_01",
      "probability": 0.342,
      "alignment_score": 0.492
    },
    {
      "word": "vocero",
      "start": 13.78,
      "end": 14.12,
      "speaker": "SPEAKER_01",
      "probability": 0.857,
      "alignment_score": 0.65
    }
  ]
}
```

**Campos requeridos:**
- `word`: texto transcrito
- `start`: tiempo inicio en segundos
- `end`: tiempo fin en segundos
- `speaker`: identificador del hablante
- `probability`: confianza 0.0-1.0

**Campos opcionales:**
- `alignment_score`: métrica de alineación

---

## 🐛 Troubleshooting

### "librosa no está disponible"
```bash
pip install librosa soundfile numpy
```

### "Archivo no encontrado"
Verifica:
- Ruta: `src/data/transcription_projects/memoria_1970_1990/`
- Nombres coinciden exactamente (mayúsculas, espacios)

### "JSON inválido"
```bash
python -m json.tool "archivo.json"  # Valida JSON
```

### "Error al procesar audio"
- Archivo .wav corrupto
- Sample rate incompatible
- Timestamps fuera de rango

---

## 📈 Escalabilidad a Producción

### Docker
```yaml
# docker-compose.yml
services:
  web_app:
    volumes:
      - ./src/data:/app/data  # Volumen para audios compartido
  postgres:  # Base de datos compartida para múltiples instancias
```

### NFS (Network File System)
Para múltiples servidores:
```bash
# En servidor NFS
mount -t nfs server:/path/to/data /mnt/data

# Actualizar en Docker
volumes:
  - /mnt/data:/app/data
```

### Redis (Caché de Audios)
Opcional para caché distribuido de segmentos frecuentes.

---

## 📚 Referencias

- [Librosa Documentation](https://librosa.org/)
- [SoundFile Documentation](https://python-soundfile.readthedocs.io/)
- [Flask API](https://flask.palletsprojects.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)

---

## 📞 Soporte

Si encuentras problemas:
1. Revisa los logs: `tail -f logs/app.log`
2. Valida el JSON: `python -m json.tool`
3. Prueba la API manualmente con curl
4. Verifica permisos de archivos: `ls -la src/data/`

