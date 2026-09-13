# AtlasAI

**AtlasAI** is an evidence-backed enterprise project intelligence platform. It connects to a project's authorized sources — documents, and (inert until credentials are configured) email, meetings, and PM tools — retrieves permission-filtered evidence, and answers scope and delivery questions with a structured, cited finding.

The core design rule: **the LLM is never the system of record.** Every material claim in an answer links back to immutable source evidence. If the evidence isn't there, the system returns `NOT_VERIFIED` instead of guessing, and any action that writes back to an external system requires a human to approve it first.

> Read [`docs/ATLASAI_MASTER_SPEC.md`](docs/ATLASAI_MASTER_SPEC.md) for the full product/engineering specification, and [`docs/ERD_FINAL.md`](docs/ERD_FINAL.md) for the database schema authority.

---

## Table of contents

- [What problem does this solve?](#what-problem-does-this-solve)
- [Core principles](#core-principles)
- [How it works](#how-it-works)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Getting started](#getting-started)
- [Environment variables](#environment-variables)
- [Running tests and checks](#running-tests-and-checks)
- [What's built vs. what's flagged as follow-on](#whats-built-vs-whats-flagged-as-follow-on)

## What problem does this solve?

On any client-facing project, "is X in scope?" or "did we deliver Y?" gets answered by digging through emails, contracts, meeting notes, and PM tickets by hand — and the answer often depends on who you ask. AtlasAI automates that lookup: it ingests the project's documents, indexes them for retrieval, and lets an AI agent produce a grounded answer that always points back to the exact source (file, page, excerpt, timestamp) it came from. When two sources disagree, or nothing addresses the question, it says so explicitly instead of fabricating an answer.

## Core principles

- **Evidence first** — every finding is backed by traceable source evidence.
- **The LLM is never the system of record** — model output is a derived artifact, not the source of truth.
- **Every material claim links to source evidence.**
- **Every query is tenant/project permission-filtered.**
- **Missing evidence produces `NOT_VERIFIED`**, never a guess.
- **External writes require human approval.**
- **Original evidence is immutable**; superseding it requires an explicit action.
- **Sensitive actions are audited.**

## How it works

```
Source systems
  → connector authorization and scope selection
  → incremental sync with cursor and retry
  → immutable source version + parsing/OCR/normalization
  → evidence chunks with location metadata
  → lexical index + vector embedding
  → permission-filtered hybrid retrieval
  → reranking and evidence packet
  → claim extraction, timeline, requirement mapping
  → conflict and supersession analysis
  → citation/policy/schema validation
  → structured, cited finding
  → human review or approved action
  → audit, metrics, evaluation
```

Every agent run moves through an explicit, bounded state machine — it cannot loop forever, call unregistered tools, or execute arbitrary code:

```
RECEIVED → CLASSIFY → PLAN → RETRIEVE → RERANK → ANALYZE → VERIFY → FINDING → ACTION_DECISION → COMPLETE
```

For requests that need to draft an external response, an approval branch is inserted before anything is sent:

```
ACTION_DECISION → PROPOSE_ACTION → WAIT_APPROVAL → EXECUTE → COMPLETE
```

Hard limits enforced on every run: max 12 steps, max 3 calls per tool, a run-level and per-tool timeout, a token budget, and an allowlist of tools — no arbitrary SQL, shell, URL, or code execution.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router) + React 18 + TypeScript, Tailwind CSS, TanStack Query, Zustand, React Hook Form + Zod |
| API | Python 3.12, FastAPI, Pydantic v2 |
| Data layer | SQLAlchemy 2.x, Alembic migrations |
| Database | PostgreSQL 16 with `pgvector` |
| Async jobs / realtime | Redis + Celery (worker + beat), Server-Sent Events for live agent progress |
| Object storage | S3-compatible (MinIO in local dev) |
| Malware scanning | ClamAV |
| Embeddings | Local sentence-transformers model (`BAAI/bge-base-en-v1.5`) served by a dedicated embedder microservice |
| LLM | Anthropic Claude (classify / default / escalation model tiers), via an internal LLM gateway with structured-output validation and cost tracking |
| Tooling | `uv` (Python workspace/dependency manager), `ruff` (lint), `mypy --strict` (types), `pytest` (tests) |
| Infra | Docker Compose for local dev; each service has its own Dockerfile |

## Repository layout

This is a `uv` workspace (Python) plus an independent Next.js app, organized as a monorepo:

```
apps/
  api/          FastAPI control plane — auth, tenants/projects, uploads,
                evidence search, approvals, audit, realtime SSE
  ai_atlas/     Data-plane runtime — Celery workers (ingestion + the
                bounded agent state machine) and the embedding microservice
  web/          Next.js 14 + TypeScript frontend
packages/
  domain/       Pure Pydantic contracts, enums, and the agent state machine
                definition — no DB/HTTP dependency
  db/           SQLAlchemy 2.x models, the tenant/project-scoped repository
                layer, object storage and Redis clients
  retrieval/    Hybrid (full-text + pgvector) search, reranking, the
                embedder HTTP client
  connectors/   The Connector protocol; manual-upload (parsers, MIME
                validation, malware scanning) and Git/CI are fully live;
                Gmail/MS Graph/Drive/Meetings/PM are real, complete
                adapters, inert until their OAuth credentials are set
  llm_gateway/  Anthropic adapter, structured-output validation,
                untrusted-evidence prompt framing, cost tracking
  evaluation/   Fixture-driven evaluation harness (9 required categories)
  security/     RBAC, credential-ref encryption, payload hashing, redaction
infra/migrations/  Alembic migrations (schema authority: docs/ERD_FINAL.md)
docs/              Product/engineering specs, ADRs, ERD
tests/             unit/, integration/, evaluation/
```

## Prerequisites

- **Docker Desktop** (with the WSL2 backend on Windows) — required to run Postgres, Redis, MinIO, ClamAV, and the embedder locally.
- **[uv](https://docs.astral.sh/uv/)** — Python package/workspace manager, if you want to run services on the host instead of purely in Docker.
- **Node.js 20+** and npm — for the frontend.
- An **Anthropic API key** — required for the agent/LLM features to function.

## Getting started

```bash
# 1. Configure environment
cp .env.example .env
# Fill in ANTHROPIC_API_KEY at minimum. Every other value already has a
# workable local default in .env.example — change secrets before any real
# deployment.

# 2. Start the full stack
docker compose up -d
```

This brings up Postgres (pgvector), Redis, MinIO, ClamAV, the embedding microservice, the API, a Celery worker + beat, and the web frontend. First boot downloads the ClamAV virus database and the embedding model, so give the `clamav` and `embedder` services a few minutes to report healthy:

```bash
docker compose ps
```

Apply database migrations (they don't run automatically at app startup, and nothing is auto-created — only Alembic creates schema):

```bash
uv run alembic -c alembic.ini upgrade head
```

Once healthy:
- Web app → http://localhost:3000
- API → http://localhost:8000 (interactive Swagger docs at `/docs`)

### Host-side development (faster iteration)

```bash
uv sync --all-packages        # Python workspace (skips the embedder's
                               # torch/sentence-transformers — see
                               # apps/ai_atlas/pyproject.toml's `embedder` extra)
cd apps/web && npm install    # frontend
```

Run the API directly on the host against the dockerized Postgres/Redis/MinIO/ClamAV/embedder for fast iteration:

```bash
uv run uvicorn atlasai_api.main:app --reload
```

## Environment variables

All configuration is documented with inline comments in [`.env.example`](.env.example) — copy it to `.env` and fill in real values. Never commit `.env`; it's already git-ignored. Key groups:

- **Core** — environment name, log level, app secret key
- **PostgreSQL / Redis / object storage** — connection details (sensible Docker defaults provided)
- **Embedding service** — model name and vector dimension
- **ClamAV** — malware-scanning host/port
- **Anthropic** — API key and which Claude model tier handles classification, default reasoning, and escalation
- **Auth/JWT** — token TTLs and signing key
- **Agent run limits** — step/tool/timeout/token budgets
- **Connectors** — GitHub (fully live), Gmail/MS Graph/Google Drive/Meetings/Jira (real adapters, inert until OAuth credentials are set)

## Running tests and checks

```bash
uv run ruff check packages apps tests                 # lint
uv run mypy packages/domain/src packages/security/src packages/db/src \
  packages/retrieval/src packages/connectors/src packages/llm_gateway/src \
  packages/evaluation/src apps/api/src apps/ai_atlas/src               # type check (strict)
uv run pytest tests/unit                               # unit tests only, no external services needed
uv run pytest tests/unit tests/integration             # needs Postgres/Redis/MinIO/ClamAV running
```

[`tests/evaluation/fixtures/`](tests/evaluation/fixtures/) holds the required evaluation categories (in-scope, out-of-scope, conflicting, ambiguous, not-verified, superseded, partially-delivered, prompt-injection, permission-boundary). Running them via `atlasai_evaluation.EvalHarness` exercises the real HTTP API end to end and needs a working `ANTHROPIC_API_KEY`.

## What's built vs. what's flagged as follow-on

**Built and verified against a real running stack:**
- Full multi-tenant schema and Alembic migrations
- Auth (JWT + revocable refresh tokens) and tenant/project RBAC, with negative-authorization tests
- Audit logging
- Manual document upload: MIME validation, ClamAV scanning, PDF/DOCX/XLSX/text/image-OCR parsing, chunking, local embeddings, hybrid retrieval, deterministic reranking
- The bounded agent state machine running asynchronously via Celery with realtime SSE progress streaming
- The approval workflow: payload-hash binding, expiry, idempotent execution
- Source deletion with tombstone propagation
- The Next.js frontend covering this whole flow

**Explicitly deferred** (per the plan agreed before this build started):
- **Gmail / MS Graph / Drive / Meetings / PM connectors** — real, complete adapter code against the `Connector` protocol, but inert until their OAuth apps are registered and credentials are set in `.env`. Git/CI (GitHub) and manual upload are the two fully live connectors today.
- **Requirements/decisions/delivery-record timelines** — full data model and repository layer exist, but there's no dedicated API/UI yet; the agent's timeline/scope-comparison/conflict-analysis tools aren't wired into the tool registry yet.
- **Full observability** (OpenTelemetry dashboards) and **production hardening** (managed backups, load testing, external red-team engagement) are out of scope for this pass — structured audit logging, retention/tombstoning, and the prompt-injection/permission-boundary evaluation fixtures are in place as the practical subset.
- The agent's **ACTION_DECISION** step currently only routes into the action/approval branch for the `DRAFT_RESPONSE` intent — broader autonomous write-intent detection is future work.
