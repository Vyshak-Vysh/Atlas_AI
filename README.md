# AtlasAI

**AtlasAI** is an evidence-backed enterprise project intelligence platform. It ingests a project's authorized sources — documents today, with email, meetings, and PM tools defined by the same connector protocol and planned next — retrieves permission-filtered evidence, and answers scope and delivery questions with a structured, cited finding.

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
RECEIVED → CLASSIFY → PLAN → INVESTIGATE → RERANK → ANALYZE → VERIFY → FINDING → ACTION_DECISION → COMPLETE
```

For requests that need to draft an external response, an approval branch is inserted before anything is sent:

```
ACTION_DECISION → PROPOSE_ACTION → WAIT_APPROVAL → EXECUTE → COMPLETE
```

**INVESTIGATE is a real tool-calling loop.** The model is handed a closed registry of read-only tools and decides for itself which to call and with what arguments — searching once for an original commitment, again for a later amendment, and checking the tracked requirement list, without any of those being hardcoded. The available tools are:

| Tool | Purpose |
|---|---|
| `search_evidence` | Hybrid keyword + semantic search over the project's evidence |
| `list_project_sources` | What documents exist at all, so "no search hit" is not mistaken for "no evidence" |
| `list_requirements` | The project's tracked requirements and their scope/delivery status |
| `get_requirement_detail` | One requirement with its acceptance criteria |

Hard limits enforced on every run: max 12 steps, max 3 calls per tool, a run-level and per-tool timeout, a token budget, and an allowlist of tools — no arbitrary SQL, shell, URL, or code execution. The allowlist and the per-tool budget are enforced at dispatch in `ToolExecutionContext.execute`, not merely described in the prompt, and every tool is scoped to the run's tenant and project server-side — no tool accepts a tenant or project argument from the model, so a poisoned prompt cannot reach another tenant's data.

The loop's prose is never the answer. Its only durable output is the set of authoritative `EvidenceCandidate` rows it gathered, which RERANK orders and ANALYZE turns into a structured, citation-validated finding. Setting `agent_runs.model_policy.retrieval_mode` to `"deterministic"` swaps the loop for RETRIEVE — one fixed hybrid search per planned subquery, no model in the loop — which is the cheaper, replayable path.

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
  domain/       Pure Pydantic contracts, enums, tool-call contracts, and
                the agent state machine definition — no DB/HTTP dependency
  db/           SQLAlchemy 2.x models, the tenant/project-scoped repository
                layer, object storage and Redis clients
  retrieval/    Hybrid (full-text + pgvector) search, reranking, the
                embedder HTTP client
  connectors/   The Connector protocol and provider registry. Manual
                upload is implemented end to end (parsers, MIME validation,
                malware scanning, chunking). Gmail/MS Graph/Drive/Meetings/
                Jira/Git-CI are defined in the provider enum and surfaced in
                the UI as unavailable; their adapters are not yet written
  llm_gateway/  Anthropic adapter, structured-output validation, the
                bounded tool-use loop, untrusted-evidence prompt framing,
                cost tracking
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
- **Connectors** — manual upload needs no configuration and is the only implemented provider. The GitHub/Gmail/MS Graph/Google Drive/Meetings/Jira variables are placeholders for adapters that are not yet written; setting them does not enable a connector

## Running tests and checks

```bash
uv run ruff check packages apps tests                 # lint
uv run mypy packages/domain/src packages/security/src packages/db/src   packages/retrieval/src packages/connectors/src packages/llm_gateway/src   packages/evaluation/src apps/api/src apps/ai_atlas/src               # type check (strict)
uv run pytest tests/unit                               # unit tests only, no external services needed
uv run pytest tests/unit tests/integration             # needs Postgres/Redis/MinIO/ClamAV running

cd apps/web && npm run typecheck && npm run test:run   # frontend types + unit tests
```

All of the above run in CI on every push and pull request
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)), with Postgres/pgvector,
Redis and MinIO brought up as services for the integration job. No job in that
workflow has an API key, by design — anything needing a live model belongs in
the evaluation workflow instead.

### Grounding evaluation

[`tests/evaluation/fixtures/`](tests/evaluation/fixtures/) holds **37 cases across the nine required categories** — in-scope, out-of-scope, conflicting, ambiguous, not-verified, superseded, partially-delivered, prompt-injection, and permission-boundary — with four or five cases each, so the metrics are computed over a sample large enough to show a regression rather than flipping between 0% and 100%.

```bash
# Runs every fixture through the real POST /api/v1/agent/runs path.
# Costs real money: one model call per case.
uv run python -m atlasai_evaluation.cli --base-url http://localhost:8000 --output eval-report.json

# Re-render an existing report as a metric table. Free, no network.
uv run python -m atlasai_evaluation.cli --summarize eval-report.json
```

The harness exercises the real HTTP API end to end and needs a working `ANTHROPIC_API_KEY`. It scores retrieval recall@k, citation coverage, unsupported-assertion rate, conflict-detection precision, prompt-injection resistance and permission-boundary enforcement, and exits non-zero when any falls below its threshold — 100% for injection resistance and permission boundaries, 95% for citation coverage, 5% maximum for unsupported assertions. It runs weekly in [`.github/workflows/evaluation.yml`](.github/workflows/evaluation.yml) and publishes the metric table as a job summary.

## What's built vs. what's flagged as follow-on

**Built and verified against a real running stack:**
- Full multi-tenant schema and Alembic migrations
- Auth (JWT + revocable refresh tokens) and tenant/project RBAC, with negative-authorization tests
- Audit logging
- Manual document upload: MIME validation, ClamAV scanning, PDF/DOCX/XLSX/text/image-OCR parsing, chunking, local embeddings, hybrid retrieval, deterministic reranking
- The bounded agent state machine running asynchronously via Celery with realtime SSE progress streaming
- **The INVESTIGATE tool-calling loop** — a four-tool read-only registry with the allowlist and per-tool call budget enforced at dispatch, each tool call checkpointed as its own `agent_steps` row. The loop's protocol behaviour (result batching, iteration bounds, refusal handling, budget exhaustion) is unit-tested against a scripted provider, so it is covered in CI without an API key
- **The GitHub connector** — issues and pull requests as evidence, with incremental cursor-based sync, tested against a mocked transport
- The approval workflow: payload-hash binding, expiry, idempotent execution
- Source deletion with tombstone propagation
- The Next.js frontend covering this whole flow
- CI running lint, strict types, unit tests, integration tests against real services, and the frontend type-check/test/build on every push

**Explicitly deferred** (per the plan agreed before this build started):
- **Gmail / MS Graph / Drive / Meetings / Jira connectors** — **not implemented.** The `Connector` protocol, the provider enum, the registry's `is_configured()` gate and the connector UI all exist and are exercised by the manual-upload and GitHub providers, so adding one is a contained piece of work — but no adapter code exists for these five, and `GET /api/v1/connectors` correctly reports them as unavailable. Manual upload and GitHub are the implemented providers today.
- **Requirements/decisions/delivery-record timelines** — full data model and repository layer exist, but there's no dedicated API/UI yet; the agent's timeline/scope-comparison/conflict-analysis tools aren't wired into the tool registry yet.
- **Full observability** (OpenTelemetry dashboards) and **production hardening** (managed backups, load testing, external red-team engagement) are out of scope for this pass — structured audit logging, retention/tombstoning, and the prompt-injection/permission-boundary evaluation fixtures are in place as the practical subset.
- The agent's **ACTION_DECISION** step currently only routes into the action/approval branch for the `DRAFT_RESPONSE` intent — broader autonomous write-intent detection is future work.
