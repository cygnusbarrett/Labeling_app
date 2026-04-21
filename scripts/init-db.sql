-- Inicialización opcional de PostgreSQL para producción.
-- La aplicación crea tablas automáticamente con SQLAlchemy.
-- Este script evita fallos de bind mount cuando docker-compose espera el archivo.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
