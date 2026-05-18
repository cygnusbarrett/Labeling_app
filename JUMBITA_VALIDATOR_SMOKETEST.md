# Jumbita Validator Smoke Test

Esta checklist valida la imagen Docker de produccion desplegada en jumbita, no el Flask local con SQLite.

## 1. Deploy de la imagen actual

```bash
ssh cdgutierrez2@jumbita.ing.uc.cl
cd /home/cdgutierrez2/docker_projects/Labeling_app
bash scripts/deploy_and_smoketest_jumbita.sh
```

Si quieres apuntar a otro proyecto o rama:

```bash
PROJECT_ID=memoria_1970_1990 GIT_BRANCH=feat/jumbita-dev-migration \
  bash scripts/deploy_and_smoketest_jumbita.sh
```

## 2. Abrir la aplicacion desplegada

Si necesitas tunel local:

```bash
ssh -N -L 3001:127.0.0.1:3000 cdgutierrez2@jumbita.ing.uc.cl
```

Luego abrir:

- http://127.0.0.1:3001/login

## 3. Validar comportamiento del validador

Comprueba visualmente que:

- el bloque de audio aparece debajo del bloque de transcripcion
- ya no existe el boton `Repetir`
- existe el boton `Confirmar con duda`
- al avanzar no aparece un falso mensaje de completado si aun quedan pendientes
- al cambiar de segmento no se arrastra audio del segmento anterior

## 4. Validar persistencia en BD

Despues de probar `Confirmar`, `Confirmar con duda` y `Descartar`, ejecutar:

```bash
cd /home/cdgutierrez2/docker_projects/Labeling_app

docker compose -f docker-compose.prod.yml exec postgres sh -lc '
export PGPASSWORD="$POSTGRES_PASSWORD"
psql -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT id, project_id, review_status, decision_type, text_revised
FROM segments
ORDER BY updated_at DESC
LIMIT 15;
"'
```

Debe verse `decision_type` con valores `confirmed`, `doubtful` o `discarded` separados de `review_status`.

## 5. Validar exports reconstruidos

```bash
cd /home/cdgutierrez2/docker_projects/Labeling_app

docker compose -f docker-compose.prod.yml exec web_app sh -lc '
ls -lh /app/data/transcription_projects/memoria_1970_1990/reconstructed_transcript.*
'
```

Archivos esperados:

- `reconstructed_transcript.json`
- `reconstructed_transcript.txt`

Si quieres regenerarlos manualmente:

```bash
cd /home/cdgutierrez2/docker_projects/Labeling_app

docker compose -f docker-compose.prod.yml exec -u root web_app sh -lc '
chown -R appuser:appuser /app/data/transcription_projects/memoria_1970_1990
'

docker compose -f docker-compose.prod.yml exec web_app \
  python scripts/rebuild_transcription_exports.py --project-id memoria_1970_1990
```