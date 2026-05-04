# Base de Datos y Reconstruccion de Transcripciones

## Tecnologia

La aplicacion usa la URL configurada en `DATABASE_URL`.

- Desarrollo por defecto: `sqlite:///labeling_app.db`
- Produccion recomendada: PostgreSQL

La tabla clave para la reconstruccion final es `segments`.

## Tablas principales

- `users`: usuarios y roles.
- `transcription_projects`: metadatos y estadisticas del proyecto.
- `segments`: un segmento completo por fila, con texto original, texto corregido, estado, decision y orden original.
- `segment_discard_reasons`: motivo del descarte cuando aplica.
- `words`: palabras del ASR asociadas a cada segmento para contexto y edicion fina.

## Columnas importantes de `segments`

- `id`: identificador del segmento.
- `project_id`: proyecto al que pertenece.
- `audio_filename`: archivo de audio origen.
- `segment_index`: orden original dentro del audio.
- `start_time`, `end_time`: limites temporales del segmento.
- `text`: transcripcion original.
- `text_revised`: transcripcion corregida.
- `review_status`: `pending`, `approved`, `corrected`, `discarded`.
- `decision_type`: `approved`, `approved_with_doubt`, `discarded`.
- `annotator_id`: usuario que reviso el segmento.
- `completed_at`: fecha de cierre.

## Como inspeccionarla

### SQLite

```bash
sqlite3 labeling_app.db
.tables
.schema segments
SELECT id, audio_filename, segment_index, review_status, decision_type FROM segments LIMIT 20;
```

### PostgreSQL

```bash
psql "$DATABASE_URL"
\dt
\d segments
SELECT id, audio_filename, segment_index, review_status, decision_type FROM segments LIMIT 20;
```

## Consulta para reconstruir la transcripcion

```sql
SELECT
  project_id,
  audio_filename,
  segment_index,
  start_time,
  end_time,
  COALESCE(text_revised, text) AS final_text,
  review_status,
  decision_type
FROM segments
WHERE project_id = 'TU_PROYECTO'
ORDER BY audio_filename, segment_index, start_time, id;
```

## Archivo de salida actualizado

Cada vez que se guarda, edita o revierte una anotacion se regeneran:

- `data/transcription_projects/<project_id>/exports/corrected_transcription.json`
- `data/transcription_projects/<project_id>/exports/corrected_transcription.txt`

Tambien puedes reconstruirlos manualmente con:

```bash
python src/scripts/rebuild_corrected_transcripts.py <project_id>
```
