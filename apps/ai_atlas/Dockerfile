# Celery worker/beat image — deliberately excludes the `embedder` extra
# (sentence-transformers + torch); see Dockerfile.embedder for that. Build
# context is the repo root (see docker-compose.yml).
FROM python:3.12-slim AS base

# tesseract-ocr: pytesseract's runtime dependency (OCR for scanned PDFs and
# standalone images). No libmagic needed — MIME sniffing uses the pure-
# Python `filetype` package instead, to keep this image's system deps small.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.4 /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/domain/pyproject.toml packages/domain/pyproject.toml
COPY packages/db/pyproject.toml packages/db/pyproject.toml
COPY packages/retrieval/pyproject.toml packages/retrieval/pyproject.toml
COPY packages/connectors/pyproject.toml packages/connectors/pyproject.toml
COPY packages/llm_gateway/pyproject.toml packages/llm_gateway/pyproject.toml
COPY packages/evaluation/pyproject.toml packages/evaluation/pyproject.toml
COPY packages/security/pyproject.toml packages/security/pyproject.toml
COPY apps/ai_atlas/pyproject.toml apps/ai_atlas/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml

COPY packages packages
COPY apps/ai_atlas apps/ai_atlas

RUN uv sync --frozen --all-packages

ENV PATH="/app/.venv/bin:$PATH"

CMD ["celery", "-A", "ai_atlas.celery_app", "worker", "--loglevel=INFO"]
