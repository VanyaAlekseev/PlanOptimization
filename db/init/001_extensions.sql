-- Расширения PostgreSQL (выполняется при первом старте контейнера).
-- TimescaleDB можно включить позже (требуется отдельный образ/пакет).

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- CREATE EXTENSION IF NOT EXISTS "timescaledb";

