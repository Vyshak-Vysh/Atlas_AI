# AtlasAI Business Design Document — v2

## 1. Purpose and business position

AtlasAI is an evidence-backed enterprise project intelligence platform. It is not a generic chatbot and not a replacement for Gmail, Microsoft 365, Drive, meeting systems, or project-management software.

Its business purpose is to reduce scope disputes, decision ambiguity, delivery uncertainty, and communication risk by creating a controlled project truth layer over authorized source systems.

## 2. Business outcomes

### Outcome A — Evidence-backed scope resolution

For any project question, AtlasAI should state whether the available evidence supports inclusion, exclusion, conflict, ambiguity, delivery, partial delivery, supersession, or non-verification.

### Outcome B — Reduced communication risk

Client-facing drafts must be generated from approved findings and must be checked for unsupported assertions and internal-only leakage.

### Outcome C — Faster project management

Users should not manually search multiple systems to reconstruct what was agreed, when it changed, who approved it, and whether it was delivered.

### Outcome D — Auditable AI

Every material claim, finding, action, approval, and access decision must be traceable.

## 3. Business operating model

### 3.1 Truth hierarchy

1. Original source evidence.
2. Immutable source version and located evidence chunk.
3. AI-extracted claim.
4. Normalized requirement, event, or timeline item.
5. Human-approved decision.
6. Finding, report, or communication draft.

Higher layers may summarize or interpret lower layers but must never silently overwrite them.

### 3.2 Evidence semantics

- An email proves that a statement was made; it does not automatically prove contractual authorization.
- A meeting summary is secondary evidence unless supported by a transcript or approved minutes.
- A later source supersedes an earlier source only when it explicitly changes, replaces, approves, or rejects it.
- Missing or inaccessible evidence produces NOT_VERIFIED, not OUT_OF_SCOPE.
- Conflicts must show both sides, dates, authors, versions, and confidence.
- Git/CI evidence corroborates delivery only when explicitly mapped to a requirement or acceptance criterion.

## 4. Roles and permission model

Permissions are evaluated at tenant, project, connector, source, and evidence visibility levels.

| Role | Main capabilities | Restrictions |
|---|---|---|
| Project Manager | Investigate, report, draft, approve | No global policy or connector ownership changes |
| AI Engineer/Admin | Configure models, connectors, evaluations, policies | Elevated approval for destructive operations |
| CEO/Sales | Executive summaries, risks, approved drafts | No unauthorized project access |
| Delivery Team | Assigned evidence and delivery status | No unrelated projects |
| Client Viewer | Approved reports and selected evidence | No internal/private evidence |
| Worker | Sync, parse, embed, evaluate | No independent external writes |

## 5. Business state model

### Requirement lifecycle

`PROPOSED → CAPTURED → VALIDATED → APPROVED → IN_PROGRESS → PARTIALLY_DELIVERED → DELIVERED_VERIFIED → SUPERSEDED`

Alternative terminal or review states:

- AMBIGUOUS
- CONFLICTING
- NOT_VERIFIED
- CANCELLED
- REJECTED

### Finding lifecycle

`DRAFT → VALIDATING → READY_FOR_REVIEW → APPROVED → PUBLISHED → SUPERSEDED`

### Action lifecycle

`PROPOSED → WAITING_APPROVAL → APPROVED → EXECUTING → EXECUTED`

Failure and rejection states:

- REJECTED
- EXPIRED
- FAILED
- CANCELLED

## 6. Detailed scope-dispute decision logic

### IN_SCOPE_SUPPORTED

Use only when direct evidence includes the feature in the requested project phase or agreed scope.

Required output:

- Requirement identifier.
- Exact supporting citations.
- Source dates and versions.
- Relevant acceptance criteria.
- Delivery status.

### OUT_OF_SCOPE_SUPPORTED

Use only when direct evidence excludes the feature or assigns it to another phase.

Required output:

- Exclusion citation.
- Phase reference.
- Any later change or approval that could supersede the exclusion.

### CONFLICTING

Use when credible evidence supports incompatible interpretations.

Required output:

- Evidence side A.
- Evidence side B.
- Dates, authors, source types, and versions.
- Why the conflict matters.
- Human decision request.

### AMBIGUOUS

Use when wording, ownership, phase, or acceptance criteria are unclear.

Required output:

- Ambiguous terms.
- Competing interpretations.
- Clarifying questions.
- Recommended decision owner.

### NOT_VERIFIED

Use when accessible evidence is insufficient.

Required output:

- What was searched.
- What was unavailable.
- What evidence would resolve the question.
- Explicit statement that absence was not proven.

### DELIVERED_VERIFIED

Use only when a requirement is linked to explicit delivery or acceptance evidence, such as a task, pull request, release, test result, acceptance record, or approved demonstration.

### PARTIAL

Use when some acceptance criteria are met and others remain open. Report criterion-level status.

### SUPERSEDED

Use when a later approved decision explicitly replaces the earlier requirement or interpretation.

## 7. Approval and external-action rules

- Drafting is not sending.
- Every external action has an immutable payload.
- Approval is bound to the exact payload hash.
- Any payload change invalidates prior approval.
- Approval must include approver identity, decision, reason, time, and expiry.
- Execution must be idempotent.
- External writes are disabled by default.
- Connector scope, user permission, project permission, and policy must all pass.
- Every proposal, approval, rejection, execution, and failure is audited.

## 8. Client-facing output policy

Client-facing content must:

- Use only approved or publishable findings.
- Exclude internal-only conversations, private notes, and internal risk commentary.
- Distinguish facts from recommendations.
- Avoid unsupported certainty.
- Include appropriate citations or a citation-backed internal review record.
- Require human editing and approval before sending.

## 9. Business acceptance criteria

A production-grade release must demonstrate:

1. Correct tenant and project isolation.
2. Source provenance and immutable version history.
3. Correct handling of supporting, contradicting, ambiguous, and missing evidence.
4. Human approval for every consequential external action.
5. No unsupported material claims in final findings.
6. Correct deletion and revocation propagation.
7. Evaluation fixtures covering positive, negative, ambiguous, conflicting, superseded, and partially delivered cases.
8. Audit records for access, search, sync, export, finding, approval, and external write events.

## 10. Recommended release stages

### Release 0 — Foundation

Tenant/project boundaries, schema, migrations, health, audit model, synthetic fixtures.

### Release 1 — Evidence vertical slice

Manual upload → parse → chunk → embed → hybrid retrieve → cited answer.

### Release 2 — Project intelligence

Requirements, timelines, claims, conflicts, findings, delivery verification.

### Release 3 — Controlled agents

Bounded state machine, tool registry, checkpoints, approval inbox.

### Release 4 — Enterprise connectors

Gmail, Microsoft Graph, Google Drive, meeting artifacts, project management.

### Release 5 — Production hardening

Evaluation, observability, cost controls, deletion, backups, restore tests, red-team testing, private beta.
