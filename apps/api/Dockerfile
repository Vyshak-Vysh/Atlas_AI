# Build context is the repo root (see docker-compose.yml) because this
# image needs every local workspace package apps/api depends on
# (atlasai-domain, atlasai-db, atlasai-security, atlasai-retrieval,
# atlasai-connectors, atlasai-llm-gateway, atlasai-evaluation) — not just
# its own directory.
FROM python:3.12-slim AS base

# libmagic/tesseract are pulled in transitively via atlasai-connectors'
# dependency tree at import time even though this image only runs the API
# (not ingestion) — kept out here deliberately; if a future endpoint in
# this app needs them directly, add libmagic1/tesseract-ocr then.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
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
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/ai_atlas/pyproject.toml apps/ai_atlas/pyproject.toml

# Source copied after manifests so dependency layers cache across code-only
# changes.
COPY packages packages
COPY apps/api apps/api
COPY apps/ai_atlas/src apps/ai_atlas/src

RUN uv sync --frozen --all-packages

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "atlasai_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
