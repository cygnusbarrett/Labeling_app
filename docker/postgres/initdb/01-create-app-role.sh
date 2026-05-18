#!/bin/sh

set -eu

if [ -z "${APP_DB_USER:-}" ] || [ -z "${APP_DB_PASSWORD:-}" ] || [ -z "${APP_DB_NAME:-}" ]; then
  echo "APP_DB_USER, APP_DB_PASSWORD y APP_DB_NAME son obligatorios para inicializar PostgreSQL" >&2
  exit 1
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  --set=app_db_user="$APP_DB_USER" \
  --set=app_db_password="$APP_DB_PASSWORD" \
  --set=app_db_name="$APP_DB_NAME" <<'EOSQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_db_user') THEN
        EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_db_user', :'app_db_password');
    ELSE
        EXECUTE format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'app_db_user', :'app_db_password');
    END IF;
END
$$;

SELECT format('GRANT ALL PRIVILEGES ON DATABASE %I TO %I', :'app_db_name', :'app_db_user') \gexec
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$APP_DB_NAME" \
  --set=app_db_user="$APP_DB_USER" <<'EOSQL'
SELECT format('GRANT ALL ON SCHEMA public TO %I', :'app_db_user') \gexec
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO PUBLIC;
EOSQL