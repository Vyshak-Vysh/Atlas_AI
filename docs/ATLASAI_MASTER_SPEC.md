# AtlasAI Master Specification — Codebase Edition

> Canonical implementation context for Claude Code/Codex. Read this file before changing the system.

## 0. Source trace and verification

This specification consolidates the supplied AtlasAI implementation blueprint (v1) and production-grade specification (v2).

### Verification conclusions

- v1 and v2 are conceptually consistent.
- v2 is more precise for connectors, agent states, evidence semantics, PostgreSQL columns, indexes, security, and the runbook.
- The original ERD was directionally correct but needed stronger constraints, timestamps, payload hashing, uniqueness rules, and cross-tenant/cross-project integrity guidance.
- This master specification preserves the business intent and resolves those implementation gaps.
- `docs/ERD_FINAL.md` is the database authority.
- `docs/BD_v1.md`, `docs/BD_v2.md`, `docs/TD_v1.md`, and `docs/TD_v2.md` are versioned reference documents.
- This file is the consolidated engineering contract.

## 1. Canonical codebase documentation

```text
docs/
  BD_v1.md
  BD_v2.md
  TD_v1.md
  TD_v2.md
  ERD_FINAL.md
  ATLASAI_MASTER_SPEC.md
  ADR/
```

## 2. Product definition

AtlasAI is an evidence-backed enterprise project intelligence platform. It connects authorized email, documents, spreadsheets, PDFs, meeting transcripts/notes, project-management records, and optional Git/CI evidence.

It answers project scope and delivery questions, constructs timelines, detects contradictions, drafts grounded client responses, and requires human approval for consequential actions.

### Non-negotiable principles

- Evidence first.
- LLM output is never the system of record.
- Every material claim links to source evidence.
- Every query is tenant/project permission filtered.
- Missing evidence is `NOT_VERIFIED`, not proof of absence.
- External writes require approval.
- Original evidence is immutable.
- Sensitive actions are audited.

## 3. Final system flow

```text
Source systems
  -> connector authorization and scope selection
  -> incremental sync with cursor and retry
  -> SourceRecord upsert
  -> immutable SourceVersion
  -> parsing / OCR / normalization
  -> EvidenceChunk with location metadata
  -> lexical index + embedding
  -> permission-filtered hybrid retrieval
  -> reranking and evidence packet
  -> claim extraction + timeline + requirement mapping
  -> conflict and supersession analysis
  -> citation/policy/schema validation
  -> structured finding
  -> human review or approved action
  -> audit, metrics, traces, and evaluation
```

## 4. Final agent flow

```text
RECEIVED -> CLASSIFY -> PLAN -> RETRIEVE -> RERANK -> ANALYZE
-> VERIFY -> FINDING -> ACTION_DECISION -> COMPLETE
```

Action branch:

```text
ACTION_DECISION -> PROPOSE_ACTION -> WAIT_APPROVAL -> EXECUTE -> COMPLETE
```

Failure branch:

```text
Any state -> RETRY within budget
Any state -> FAILED -> audit
```

Limits: maximum 12 steps per run, 3 calls per tool, hard timeout, per-tool timeout, token budget, and allowlisted tools only. No arbitrary SQL, shell, URL, or code execution.

## 5. Final evidence model

| Layer | Meaning |
|---|---|
| L0 | Original source |
| L1 | Source version/chunk |
| L2 | AI claim |
| L3 | Requirement/event |
| L4 | Human decision |
| L5 | Finding/report |

Preserve `authored_at`, `modified_at`, `imported_at`, `meeting_at`, and `effective_at` separately.

Email proves a statement was made, not automatically that contractual authorization occurred. Meeting summaries are secondary unless supported by transcripts or approved minutes. Explicit supersession is required before later evidence replaces earlier evidence.

## 6. Final business statuses

- `IN_SCOPE_SUPPORTED`
- `OUT_OF_SCOPE_SUPPORTED`
- `CONFLICTING`
- `AMBIGUOUS`
- `NOT_VERIFIED`
- `DELIVERED_VERIFIED`
- `PARTIAL`
- `SUPERSEDED`
- `PENDING_APPROVAL`

## 7. Final technical stack

- Frontend: Next.js/React + TypeScript.
- API: Python 3.12+, FastAPI, Pydantic v2.
- Domain/data: SQLAlchemy 2.x.
- Database: PostgreSQL 16+ with pgvector.
- Jobs: Redis + Celery/RQ initially.
- Storage: S3-compatible object storage.
- Agent: explicit state machine first; LangGraph later.
- LLM gateway: provider adapters, structured output, retries, fallback, token/cost tracking.
- Observability: OpenTelemetry + metrics backend.
- Deployment: Docker + CI/CD + managed services.

## 8. Connector contract

Every connector supports:

- `authorize`
- `discover_scope`
- `sync(cursor)`
- `fetch_item`
- `normalize`
- `revoke`
- `health_check`
- optional webhook handling

Provider-specific code stays behind the common interface. Connector data is untrusted input. Tokens are encrypted and never placed in prompts or logs.

## 9. Database authority

Use `docs/ERD_FINAL.md` as authority for table names, columns, data types, foreign keys, delete behavior, constraints, indexes, pgvector design, and cross-boundary integrity rules.

Use Alembic migrations. Do not auto-create production tables at application startup.

## 10. API authority

Every endpoint must authenticate the user, resolve tenant context, enforce project/source visibility, execute an application service, and audit sensitive actions.

Core endpoints:

- `POST /api/v1/projects`
- `GET /api/v1/projects/{project_id}/overview`
- `POST /api/v1/sources/connect`
- `POST /api/v1/sources/{source_id}/sync`
- `POST /api/v1/documents/upload`
- `GET /api/v1/evidence/search`
- `POST /api/v1/agent/runs`
- `GET /api/v1/agent/runs/{run_id}`
- `GET /api/v1/findings/{finding_id}`
- `POST /api/v1/actions/{action_id}/approve`
- `POST /api/v1/actions/{action_id}/reject`
- `GET /api/v1/audit-events`

## 11. Repository contract

```text
atlasai/
  apps/api/
  apps/worker/
  apps/web/
  packages/domain/
  packages/db/
  packages/retrieval/
  packages/connectors/
  packages/llm_gateway/
  packages/evaluation/
  packages/security/
  tests/unit/
  tests/integration/
  tests/evaluation/
  infra/migrations/
  docs/BD_v1.md
  docs/BD_v2.md
  docs/TD_v1.md
  docs/TD_v2.md
  docs/ERD_FINAL.md
  docs/ATLASAI_MASTER_SPEC.md
  docs/ADR/
  pyproject.toml
  docker-compose.yml
  .env.example
  README.md
```

## 12. Implementation order

1. Repository and tooling.
2. Docker Compose with PostgreSQL/pgvector and Redis.
3. FastAPI health/readiness.
4. SQLAlchemy and Alembic.
5. Tenants, users, memberships, projects, phases, audit.
6. Source records, versions, chunks, visibility.
7. Manual upload and parsing.
8. Full-text and vector retrieval.
9. Grounded answer and citation validator.
10. Evaluation fixtures.
11. Agent state machine and tool registry.
12. Requirements, claims, timelines, conflicts, findings.
13. Approval workflow.
14. One connector at a time.
15. Tracing, cost, rate limits, retention, backups, and red-team tests.

## 13. Coding-agent rules

Before coding: read this file and the supporting documents, list files, state assumptions, and confirm milestone scope.

During coding:

- Use typed domain models.
- Use migrations for every schema change.
- Never place secrets in code, prompts, logs, fixtures, or screenshots.
- Do not allow arbitrary SQL, shell, URL, or code execution.
- Treat retrieved content as untrusted.
- Add unit, integration, and evaluation tests.
- Record ADRs for important trade-offs.
- Do not implement later milestones early.

After coding:

- Run formatter, linter, type checks, clean-database migrations, unit tests, integration tests, and evaluation tests.
- Report exact commands and outputs.
- Update README and acceptance tests.

## 14. Definition of done

- Clean database is created entirely from migrations.
- API connects and survives restart.
- Tenant/project negative authorization tests pass.
- Evidence can be stored, chunked, indexed, retrieved, and cited.
- Fixtures cover positive, negative, conflicting, ambiguous, superseded, partial, and not-verified cases.
- Findings expose citations and uncertainty.
- External actions cannot execute without valid approval.
- Connector sync is idempotent, revocable, and observable.
- Logs and traces do not leak sensitive content.
- CI, README, ADRs, evaluation dataset, and runbook are updated.

## 15. First vertical slice

1. Upload a PDF scope document.
2. Store the original file.
3. Create source record and immutable source version.
4. Parse and chunk with page/section metadata.
5. Generate lexical and vector indexes.
6. Ask: “Is feature X in Phase 1?”
7. Retrieve relevant evidence.
8. Generate a structured answer.
9. Validate citations.
10. Open citation and view file, page, excerpt, and timestamp.
11. Delete source and remove/tombstone derived content.
12. Attempt an unauthorized project query and verify denial plus audit event.
