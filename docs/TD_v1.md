# AtlasAI Technical Design Document — v1

## 1. Architecture principles

- Evidence is the system of record.
- The LLM is an analysis component, not a database.
- Every query is tenant/project permission filtered.
- External writes require human approval.
- Connectors are revocable and incremental.
- Jobs are retry-safe and idempotent.

## 2. System architecture

| Layer | Components | Responsibility |
|---|---|---|
| UI | Next.js/React, evidence viewer, timeline, reports, approval inbox | User interaction |
| API | FastAPI, Pydantic, JWT/OAuth | Typed API and authorization |
| Orchestration | LangGraph or explicit state machine | Retrieval, analysis, checkpoints |
| Ingestion | Connector workers, parsers, OCR | Import and normalize evidence |
| Retrieval | PostgreSQL, pgvector, full text, reranker | Hybrid search |
| LLM gateway | Provider adapters, structured validation | Model abstraction and cost |
| Jobs | Redis + Celery/RQ | Sync and background work |
| Storage | PostgreSQL + S3-compatible object storage | Metadata and raw files |
| Observability | OpenTelemetry and metrics | Traces, latency, errors, tokens |
| Security | RBAC, encryption, audit | Access and compliance |

## 3. Connectors

Required connector capabilities:

- authorize
- discover scope
- incremental sync
- cursor/state tracking
- fetch item
- normalize
- revoke
- health check
- retries and rate-limit handling
- source IDs and timestamps

Sources:

- Gmail or Microsoft Graph email.
- Google Drive, OneDrive, SharePoint.
- Meeting transcripts and notes.
- Project-management tasks, comments, milestones, and status.
- Manual PDF, DOCX, XLSX, TXT, and screenshots.
- Optional Git/CI delivery evidence.

## 4. Canonical evidence model

- SourceRecord: immutable identity of an external item.
- SourceVersion: version or revision.
- EvidenceChunk: searchable located text/table segment.
- Claim: normalized statement extracted from evidence.
- Requirement: project expectation.
- RequirementEvidence: support or contradiction link.
- Decision: human-approved interpretation.
- DeliveryRecord: implementation evidence.
- Finding: assessment with status, confidence, rationale, and citations.

## 5. AI workflow

1. Receive question and context.
2. Classify intent.
3. Create retrieval subqueries.
4. Retrieve using lexical and vector search.
5. Rerank and deduplicate.
6. Build evidence packet.
7. Extract claims and analyze contradictions.
8. Generate structured finding.
9. Validate citations and permissions.
10. Propose external action if requested.
11. Persist trace and result.

## 6. Agent tools

Read tools:

- search_evidence
- get_source_record
- get_requirement_timeline
- compare_scope_versions
- analyze_conflict
- search_delivery_records

Write/proposal tools:

- draft_client_response
- create_review_task
- export_report
- send_email — disabled by default, approval required

## 7. API surface

- POST `/api/v1/projects`
- GET `/api/v1/projects/{project_id}/overview`
- POST `/api/v1/sources/connect`
- POST `/api/v1/sources/{source_id}/sync`
- POST `/api/v1/documents/upload`
- GET `/api/v1/evidence/search`
- POST `/api/v1/agent/runs`
- GET `/api/v1/agent/runs/{run_id}`
- GET `/api/v1/findings/{finding_id}`
- POST `/api/v1/actions/{action_id}/approve`
- POST `/api/v1/actions/{action_id}/reject`
- GET `/api/v1/evaluations/runs`
- GET `/api/v1/audit-events`

## 8. Non-functional requirements

- Tenant isolation on every query.
- Citation and retrieval timestamp for every answer.
- Encrypted connector tokens.
- Agent step, timeout, token, and tool limits.
- External writes disabled by default.
- Idempotent background jobs.
- Revocation and deletion propagation.
- Model version, prompt version, latency, token, cost, and outcome tracking.
- Redaction of sensitive evidence.
- Migrations, tests, CI, backups, and disaster recovery.

## 9. Implementation order

1. Repository, Docker, environment, CI.
2. PostgreSQL, pgvector, Redis, health.
3. Schema and migrations.
4. Authentication and authorization.
5. Source records, versions, chunks, audit.
6. Manual ingestion.
7. Hybrid retrieval.
8. Grounded Q&A.
9. Evaluation fixtures.
10. Agent state machine.
11. Findings, timelines, approvals.
12. Connectors.
13. Observability and production hardening.
