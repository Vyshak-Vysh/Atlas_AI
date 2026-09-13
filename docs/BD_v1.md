# AtlasAI Business Design Document — v1

## 1. Document control

- Product: AtlasAI — Enterprise Project Truth & Scope Intelligence Platform
- Version: BD v1.0
- Source basis: supplied AtlasAI TD/BD/ERD Implementation Blueprint
- Business posture: proposed implementation blueprint
- Primary principle: evidence first; inference second; human approval for decisions and external actions

## 2. Business problem

Project scope and delivery truth is distributed across client and internal email, documents, spreadsheets, meetings, meeting notes, task-management systems, and delivery artifacts. During a project phase, a client may claim that a feature was already included while the delivery team believes it is outside the agreed scope.

AtlasAI creates a project truth layer without replacing the original systems. It retrieves evidence, preserves provenance, builds a timeline, compares conflicting statements, and produces a cited finding.

AtlasAI must not behave as an autonomous judge. It must show what the available evidence supports, what remains uncertain, and where human review is required.

## 3. Business objectives

1. Connect approved evidence sources.
2. Create a unified project knowledge base with provenance and version history.
3. Answer scope and delivery questions with citations.
4. Build requirement and decision timelines.
5. Detect contradictions across documents, messages, meetings, and delivery records.
6. Draft grounded client communications.
7. Require human approval before external communication or record mutation.
8. Provide auditability, evaluation, observability, and cost tracking.

## 4. Non-goals

- Automatically declaring a client or employee correct.
- Automatically sending external email in the first release.
- Replacing project-management systems.
- Training a foundation model from scratch.
- Training models on private company data without authorization.
- Treating LLM output as the system of record.

## 5. Personas and permissions

### Project Manager / Technical Communicator

Can ask questions, inspect evidence, create reports, draft responses, and approve actions. Cannot change connector ownership or global policies.

### AI Engineer / Administrator

Can configure sources, ingestion, evaluation, models, policies, and system health. Production destructive actions require elevated approval.

### CEO / Sales

Can review executive summaries, scope risks, and client communication drafts. Can access only authorized projects.

### Delivery Team

Can view assigned project evidence and delivery status. Cannot access unrelated projects.

### Client Viewer

Optional later role. Can view approved reports and selected evidence only. Internal/private conversations remain hidden unless explicitly shared.

### System Worker

Performs sync, parsing, OCR, embedding, and evaluation work. Has no independent external communication authority.

## 6. Core business rules

- BR-001: Every project belongs to exactly one tenant/company.
- BR-002: Users can access only explicitly authorized projects and sources.
- BR-003: Imported records retain external IDs and URLs where available.
- BR-004: Original evidence is immutable. Corrections create versions or annotations.
- BR-005: AI claims require linked evidence and confidence metadata.
- BR-006: Every finding has status, confidence, timestamp, and citations.
- BR-007: Conflicting evidence must be displayed, not silently resolved.
- BR-008: Authored, modified, imported, meeting, and effective timestamps are distinct.
- BR-009: A requirement belongs to one project and may be mapped to multiple phases.
- BR-010: Requirements may have supporting and contradicting evidence links.
- BR-011: Decisions require approver, time, rationale, and evidence.
- BR-012: External actions require human approval.
- BR-013: Approval is tied to a payload hash and expires if the payload changes.
- BR-014: Revoked connectors stop future sync immediately.
- BR-015: Deletion removes or tombstones derived searchable content according to policy.
- BR-016: Client-facing drafts cannot expose internal-only evidence.
- BR-017: Reports distinguish facts, inferences, unresolved questions, and recommendations.
- BR-018: Retrieval failure is not evidence of absence.
- BR-019: Delivery status requires explicit delivery evidence or is marked unverified.
- BR-020: Sensitive actions and access decisions are audited.

## 7. Business workflows

### 7.1 Project onboarding

1. Create tenant and project.
2. Assign members and roles.
3. Connect approved sources.
4. Select sync scope and retention policy.
5. Run initial ingestion.
6. Review ingestion health and evidence coverage.

### 7.2 Scope dispute investigation

1. User selects a project.
2. User asks whether a feature is included in a phase.
3. System retrieves scope documents, emails, meetings, and task records.
4. System groups evidence by requirement.
5. System builds a timeline.
6. System compares supporting and contradicting statements.
7. System returns status, confidence, citations, and missing evidence.
8. User confirms or creates a human decision record.
9. The decision becomes a new auditable project fact; it does not overwrite original evidence.

### 7.3 Client response drafting

1. User requests a response.
2. System uses approved findings.
3. Draft is checked for unsupported claims and internal-only leakage.
4. User edits and approves.
5. Optional sending occurs only through an enabled connector.
6. Sent message ID and audit event are stored.

### 7.4 Source synchronization

1. Fetch provider delta using cursor.
2. Upsert canonical source record.
3. Create immutable source version when content changes.
4. Parse and normalize content.
5. Create evidence chunks.
6. Generate embeddings and lexical indexes.
7. Update sync metrics.
8. Persist errors and retry safely.

## 8. Finding output contract

```json
{
  "question": "...",
  "project_id": "uuid",
  "status": "CONFLICTING_EVIDENCE",
  "summary": "...",
  "facts": [],
  "inferences": [],
  "contradictions": [],
  "missing_evidence": [],
  "timeline": [],
  "citations": [],
  "confidence": 0.0,
  "recommended_next_step": "...",
  "requires_human_review": true
}
```

## 9. Scope statuses

- SUPPORTED_IN_SCOPE
- SUPPORTED_OUT_OF_SCOPE
- CONFLICTING_EVIDENCE
- AMBIGUOUS
- NOT_FOUND
- DELIVERED
- PARTIALLY_DELIVERED
- PENDING_APPROVAL

## 10. Business metrics

- Evidence citation coverage.
- Retrieval Recall@K.
- Grounded answer rate.
- Conflict detection precision.
- Unsupported assertion rate.
- Approval compliance.
- Connector freshness.
- p95 investigation latency.
- Cost per investigation.

## 11. Business acceptance

AtlasAI is acceptable for a first vertical slice when a user can upload a scope PDF, inspect extracted page-level evidence, ask whether a feature belongs to Phase 1, receive a structured cited answer, open the citation, delete the source, and receive an authorization denial when querying an unrelated project.
