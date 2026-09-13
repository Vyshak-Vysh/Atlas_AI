-- Runs once, only against a brand-new Postgres data directory (mounted into
-- /docker-entrypoint-initdb.d/). Alembic's own first migration repeats these
-- calls idempotently as a safety net for databases that skip this init path
-- (e.g. a restored backup or a managed cloud Postgres instance).
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS vector;
