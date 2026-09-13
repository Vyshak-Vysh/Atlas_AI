# ADR-0003: The embedding model runs as its own long-lived microservice

## Status

Accepted.

## Context

Both the interactive evidence-search path (`apps/api`) and batch ingestion
(`apps/ai_atlas`'s Celery workers) need embeddings. Loading
`BAAI/bge-base-en-v1.5` (~440MB) inside every Celery worker process (or
every API replica) would mean reloading it on every prefork/autoscale
event.

## Decision

Serve the model from one dedicated FastAPI process
(`apps/ai_atlas/embedder_service`, its own `Dockerfile.embedder`), loaded
once at startup. Every consumer — `packages/retrieval.EmbedderClient` —
talks to it over the internal Docker network (`http://embedder:8090`,
never exposed to the host) rather than loading the model itself. This also
keeps `torch`/`sentence-transformers` out of the API and worker images
entirely (see `apps/ai_atlas/pyproject.toml`'s `embedder` extra).

## Consequences

- One more service to run and health-check, but a strictly simpler
  operational story than "N processes each holding a model in memory."
- The embedder is a single point of failure for both search and
  ingestion; it has its own `/health` endpoint and a Docker healthcheck,
  and `docker-compose.yml` gates the worker's startup on it being healthy.
