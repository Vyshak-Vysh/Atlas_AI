# ADR-0001: `apps/ai_atlas/` instead of `apps/worker/`

## Status

Accepted.

## Context

`docs/ATLASAI_MASTER_SPEC.md` §11's repository contract lists `apps/worker/`.
The user's explicit requested repository layout for this build names the
same conceptual service `apps/ai_atlas/`.

## Decision

Build `apps/ai_atlas/` as the data-plane runtime (Celery workers for
ingestion and the bounded agent state machine, plus the embedding
microservice) — the explicit, more specific instruction governs over the
master spec's generic `apps/worker/` naming. The two names refer to the
same architectural role; no functionality changes as a result.

## Consequences

Anyone cross-referencing `ATLASAI_MASTER_SPEC.md` §11 literally should read
`apps/worker/` there as `apps/ai_atlas/` in this codebase.
