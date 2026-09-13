# ADR-0006: Evaluation runs reuse `agent_runs`/`findings`, no separate schema

## Status

Accepted.

## Context

`docs/ERD_FINAL.md` has no `evaluation_runs` table, and `GET
/api/v1/evaluations/runs` appears in the API contract without an
accompanying schema addition.

## Decision

`packages/evaluation`'s `EvalHarness` runs every fixture case through the
real `POST /api/v1/agent/runs` HTTP path — the same code path a real user
question takes — inside a dedicated per-case tenant/project created by the
harness itself, rather than inserting synthetic rows directly into the
database or inventing a parallel evaluation schema. This means the
evaluation harness tests the actual system, not a shadow implementation of
it, and `GET /api/v1/evaluations/runs` (not yet implemented as a distinct
endpoint) can be built later as a filtered view over `agent_runs`/
`findings` rather than requiring new tables.

## Consequences

Evaluation traffic is indistinguishable from production traffic in the
database except by tenant — acceptable for this build, and revisit if
evaluation volume grows enough to warrant tagging/filtering support beyond
"a differently-named tenant per eval run."
