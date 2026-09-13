# ADR-0002: `BAAI/bge-base-en-v1.5` (768-dim) instead of the ERD's literal `vector(1536)` default

## Status

Accepted.

## Context

`docs/ERD_FINAL.md` specifies `evidence_chunks.embedding vector(1536)` but
explicitly notes: "Initial embedding dimension: 1536, configurable." The
1536 figure matches OpenAI's `text-embedding-3-small`. This build's
decision (made with the user before implementation started) is to use a
locally-run open embedding model instead of a paid embedding API, so no
`OPENAI_API_KEY` is required to run the system.

## Decision

Use `BAAI/bge-base-en-v1.5` (768 dimensions, MIT license) via
`sentence-transformers`, served from a dedicated long-lived microservice
(`apps/ai_atlas/embedder_service`) rather than loaded per Celery worker
process — see ADR-0003. `evidence_chunks.embedding` is `vector(768)`, not
`vector(1536)`.

Two correctness details enforced in one place
(`embedder_service/model.py`) rather than left to callers:

1. BGE is asymmetric — queries need the instruction prefix
   `"Represent this sentence for searching relevant passages: "`; passages
   do not.
2. Embeddings are L2-normalized before storage so pgvector's
   `vector_cosine_ops` behaves as intended.

## Consequences

- Re-embedding is required if the model is ever changed; `evidence_chunks
  .embedding_model` already tracks which model produced each row, per the
  ERD.
- Changing the embedding dimension in the future is a schema migration,
  not a runtime toggle — `EMBEDDING_DIMENSION` in `packages/db/settings.py`
  fixes the pgvector column width at class-definition time.
- CPU-only inference throughput (~100-300 short passages/minute at
  batch 16-32) is adequate for interactive use and moderate ingestion
  volume; a large historical backfill would benefit from GPU inference or
  a smaller model (`BAAI/bge-small-en-v1.5`, 384-dim) — noted as a future
  option, not implemented.
