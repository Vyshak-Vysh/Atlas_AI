# AtlasAI Technical Design Document — v2

## 1. Technical scope

AtlasAI is a multi-tenant, evidence-first, production-oriented system for project truth, scope dispute analysis, requirement timelines, delivery verification, and controlled communication drafting.

Recommended baseline:

- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- PostgreSQL 16+
- pgvector
- Redis
- Celery/RQ initially
- S3-compatible object storage
- Next.js/React + TypeScript
- OpenTelemetry
- Docker and CI/CD
- Explicit state machine first; LangGraph only after the domain contracts are stable

## 2. Refined architecture flow

```text
User/UI
  ↓
FastAPI API
  ↓
Authentication + tenant/project authorization
  ↓
Application service
  ↓
Agent run coordinator
  ↓
Intent + risk classification
  ↓
Query planner
  ↓
Permission-filtered hybrid retrieval
  ├─ PostgreSQL full-text search
  ├─ pgvector similarity search
  └─ optional reranker
  ↓
Evidence packet builder
  ↓
Claim extraction + timeline normalization + conflict analysis
  ↓
Citation and policy validator
  ↓
Structured finding
  ↓
Human review when required
  ↓
Optional approved action
  ↓
Audit + metrics + trace
```

## 3. Connector contract

Every provider adapter must implement:

```python
class Connector(Protocol):
    async def authorize(self, request: AuthorizationRequest) -> AuthorizationResult: ...
    async def discover_scope(self, account: AccountRef) -> list[ScopeItem]: ...
    async def sync(self, cursor: str | None) -> SyncPage: ...
    async def fetch_item(self, external_id: str) -> ExternalItem: ...
    async def normalize(self, item: ExternalItem) -> NormalizedSource: ...
    async def revoke(self) -> None: ...
    async def health_check(self) -> HealthResult: ...
```

Connector rules:

- Provider code stays behind the interface.
- Store external IDs and source URLs.
- Support delta/cursor sync.
- Deduplicate webhook and sync events.
- Preserve provider timestamps.
- Encrypt credential references.
- Stop future sync immediately on revocation.
- Never place access tokens in prompts, logs, or source text.
- Treat imported content as untrusted input.

## 4. Provider-specific requirements

### Gmail

- Threads, messages, headers, attachments.
- Preserve thread ID, message ID, sender, recipients, authored time, modified/imported time.
- Apply least-privilege scopes.
- Scan attachments and validate MIME type.

### Microsoft Graph

- Mail, OneDrive, SharePoint, Teams artifacts.
- Use delegated/application scopes intentionally.
- Support delta queries.
- Restrict sites, drives, mailboxes, and Teams sources.

### Google Drive

- Docs, Sheets, Slides, PDFs, revisions.
- Preserve revision IDs.
- Store sheet/tab/cell locations.
- Respect source permissions and export restrictions.

### Meeting systems

- Transcript text.
- Speaker identity where authorized.
- Start/end timestamps.
- Notes and summaries.
- Distinguish original transcript from generated summary.

### Project management

- Tasks, comments, milestones, status, assignees.
- Preserve external IDs.
- Support webhook dedupe.
- Map task and acceptance evidence to requirements.

### Manual upload

- PDF, DOCX, XLSX, TXT, images.
- MIME and size validation.
- Malware scanning.
- OCR fallback.
- Store original object separately from extracted text.

### Git/CI

- PRs, commits, releases, test evidence.
- Corroboration only unless explicitly mapped to a requirement or acceptance criterion.

## 5. Agent state machine

```text
RECEIVED
  → CLASSIFY
  → PLAN
  → RETRIEVE
  → RERANK
  → ANALYZE
  → VERIFY
  → FINDING
  → ACTION_DECISION
  → COMPLETE
```

Action branch:

```text
ACTION_DECISION
  → PROPOSE_ACTION
  → WAIT_APPROVAL
  → EXECUTE
  → COMPLETE
```

Failure branch:

```text
Any state → RETRY within budget
Any state → FAILED → audited terminal state
```

State contracts:

- RECEIVED: validate identity, project, and permissions.
- CLASSIFY: determine intent and risk.
- PLAN: create subqueries and allowlisted tools.
- RETRIEVE: permission-filtered hybrid search.
- RERANK: deduplicate, score, and diversify evidence.
- ANALYZE: extract claims, events, requirements, and conflicts.
- VERIFY: validate citations, permissions, output schema, and unsupported claims.
- FINDING: persist structured assessment.
- ACTION_DECISION: determine whether a write is requested.
- PROPOSE_ACTION: freeze action payload and hash.
- WAIT_APPROVAL: validate approver, expiry, scope, and hash.
- EXECUTE: perform idempotent approved write.
- FAILED: safe error, retry metadata, and audit.

Default safety limits:

- Maximum 12 steps per run.
- Maximum 3 calls per tool.
- Hard execution timeout.
- Per-tool timeout.
- Token budget.
- Allowlisted tools only.
- No arbitrary shell, SQL, URL fetching, or code execution.

## 6. Evidence truth model

| Layer | Object | Meaning |
|---|---|---|
| L0 | Original source | Immutable record of what was written/created |
| L1 | Source version/chunk | Searchable representation with location |
| L2 | Claim | AI-extracted statement linked to evidence |
| L3 | Requirement/event | Normalized project interpretation |
| L4 | Human decision | Approved interpretation with rationale |
| L5 | Finding/report | Facts, inference, uncertainty, recommendation |

Mandatory timestamp fields:

- authored_at
- modified_at
- imported_at
- meeting_at
- effective_at

Rules:

- Explicit supersession only.
- Email is evidence of a statement, not automatic authorization.
- Meeting summaries are secondary unless supported.
- Conflicts show both sides.
- Retrieval failure is NOT_VERIFIED.

## 7. Retrieval architecture

### Candidate generation

1. Normalize query.
2. Apply tenant/project/source visibility filters.
3. Run PostgreSQL full-text search.
4. Run pgvector cosine similarity search.
5. Merge candidates.
6. Deduplicate by source/version/chunk.
7. Rerank using relevance, source authority, recency, exact phrase overlap, and requirement mapping.
8. Build an evidence packet with excerpts and locations.

### pgvector design

- Initial embedding dimension: 1536, configurable.
- Store embedding model identifier per chunk.
- Do not mix dimensions in one vector column.
- Benchmark HNSW versus IVFFlat.
- Use cosine distance for semantic retrieval.
- Re-embed when the embedding model changes.
- Keep deleted chunks excluded from retrieval.
- Combine vector retrieval with lexical search rather than using embeddings alone.

## 8. API contracts

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

Every endpoint must enforce tenant and project authorization.

## 9. Observability and evaluation

Record:

- Request ID.
- Tenant and project IDs.
- Agent run and step IDs.
- Model/provider/version.
- Prompt/template version.
- Retrieval query and filters.
- Candidate counts and scores.
- Latency.
- Input/output tokens.
- Cost.
- Errors and retries.
- Citation validation result.
- Human review result.

Evaluation dataset must contain:

- In-scope.
- Out-of-scope.
- Conflicting.
- Ambiguous.
- Not verified.
- Superseded.
- Partially delivered.
- Prompt-injection attempts.
- Permission boundary cases.

## 10. Security gates

- OIDC/OAuth2.
- Least-privilege connector scopes.
- Encrypted credentials.
- Tenant/project/source checks on every read.
- Imported content treated as untrusted prompt content.
- No arbitrary SQL, shell, URL, or code execution.
- Approval + payload hash + expiry + idempotency for external writes.
- Redaction in logs and client drafts.
- Retention and deletion propagation.
- Backups and restore tests.
- Malware scanning.
- Written authorization before real company/client data.

## 11. Implementation order

1. Repository and developer tooling.
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
15. Tracing, cost, rate limits, retention, backups, red-team tests.
