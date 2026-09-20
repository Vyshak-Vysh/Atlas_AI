"""Status/type enums shared across services.

The corresponding database columns are plain ``varchar`` (per
``docs/ERD_FINAL.md``, which intentionally avoids Postgres ``ENUM`` types so
new values never require a migration). These Python enums are the single
place that values are validated at the service/API boundary.
"""

from __future__ import annotations

from enum import StrEnum


class TenantStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"


class MembershipRole(StrEnum):
    """Roles per BD_v2 §4. Used for both tenant_members.role and project_members.role."""

    PROJECT_MANAGER = "PROJECT_MANAGER"
    AI_ENGINEER_ADMIN = "AI_ENGINEER_ADMIN"
    CEO_SALES = "CEO_SALES"
    DELIVERY_TEAM = "DELIVERY_TEAM"
    CLIENT_VIEWER = "CLIENT_VIEWER"
    WORKER = "WORKER"


class ProjectStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class PhaseStatus(StrEnum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class SpaceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    ARCHIVED = "ARCHIVED"


class SprintStatus(StrEnum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ConnectorProvider(StrEnum):
    MANUAL_UPLOAD = "MANUAL_UPLOAD"
    GIT_CI_GITHUB = "GIT_CI_GITHUB"
    GMAIL = "GMAIL"
    MSGRAPH = "MSGRAPH"
    GOOGLE_DRIVE = "GOOGLE_DRIVE"
    MEETINGS = "MEETINGS"
    PM_JIRA = "PM_JIRA"


class ConnectorStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    REVOKED = "REVOKED"
    ERROR = "ERROR"


class SourceVisibility(StrEnum):
    """Controls which roles a source's derived evidence is visible to.

    PROJECT: all project members (default).
    INTERNAL: hidden from CLIENT_VIEWER (BR-016 — internal-only evidence
        must never leak into client-facing drafts).
    CLIENT_SHARED: explicitly cleared for CLIENT_VIEWER visibility.
    """

    PROJECT = "PROJECT"
    INTERNAL = "INTERNAL"
    CLIENT_SHARED = "CLIENT_SHARED"


class SyncRunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class RequirementStatus(StrEnum):
    """Requirement lifecycle per BD_v2 §5."""

    PROPOSED = "PROPOSED"
    CAPTURED = "CAPTURED"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    PARTIALLY_DELIVERED = "PARTIALLY_DELIVERED"
    DELIVERED_VERIFIED = "DELIVERED_VERIFIED"
    SUPERSEDED = "SUPERSEDED"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICTING = "CONFLICTING"
    NOT_VERIFIED = "NOT_VERIFIED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class TaskStatus(StrEnum):
    """Day-to-day task workflow state for a Requirement, tracked in the
    `requirements.task_status` column.

    This is a SEPARATE axis from `RequirementStatus`: `RequirementStatus`
    answers "is this in scope and has evidence verified its delivery?";
    `TaskStatus` answers "where is this item on the team's kanban board
    right now?". The two must never be merged into one enum — a
    requirement can be `TaskStatus.DONE` from the assignee's point of view
    while still `RequirementStatus.NOT_VERIFIED` until evidence confirms it.
    """

    TO_DO = "TO_DO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"
    BLOCKED = "BLOCKED"


class TaskPriority(StrEnum):
    URGENT = "URGENT"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class ClaimType(StrEnum):
    SCOPE_STATEMENT = "SCOPE_STATEMENT"
    DELIVERY_STATEMENT = "DELIVERY_STATEMENT"
    APPROVAL_STATEMENT = "APPROVAL_STATEMENT"
    EXCLUSION_STATEMENT = "EXCLUSION_STATEMENT"
    OTHER = "OTHER"


class ClaimPolarity(StrEnum):
    ASSERTS = "ASSERTS"
    DENIES = "DENIES"
    QUESTIONS = "QUESTIONS"


class RequirementEvidenceRelationType(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    CLARIFIES = "CLARIFIES"
    SUPERSEDES = "SUPERSEDES"


class DecisionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DeliveryRecordStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PARTIAL = "PARTIAL"
    DELIVERED_VERIFIED = "DELIVERED_VERIFIED"
    REJECTED = "REJECTED"


class AgentRunStatus(StrEnum):
    RECEIVED = "RECEIVED"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentRunIntent(StrEnum):
    SCOPE_QUESTION = "SCOPE_QUESTION"
    DELIVERY_QUESTION = "DELIVERY_QUESTION"
    CONFLICT_CHECK = "CONFLICT_CHECK"
    DRAFT_RESPONSE = "DRAFT_RESPONSE"
    EXPORT_REPORT = "EXPORT_REPORT"
    EVALUATION = "EVALUATION"


class FindingStatus(StrEnum):
    """Canonical finding statuses per ATLASAI_MASTER_SPEC.md §6."""

    IN_SCOPE_SUPPORTED = "IN_SCOPE_SUPPORTED"
    OUT_OF_SCOPE_SUPPORTED = "OUT_OF_SCOPE_SUPPORTED"
    CONFLICTING = "CONFLICTING"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_VERIFIED = "NOT_VERIFIED"
    DELIVERED_VERIFIED = "DELIVERED_VERIFIED"
    PARTIAL = "PARTIAL"
    SUPERSEDED = "SUPERSEDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"


class ActionType(StrEnum):
    DRAFT_CLIENT_RESPONSE = "DRAFT_CLIENT_RESPONSE"
    CREATE_REVIEW_TASK = "CREATE_REVIEW_TASK"
    EXPORT_REPORT = "EXPORT_REPORT"
    SEND_EMAIL = "SEND_EMAIL"


class ActionStatus(StrEnum):
    """Action lifecycle per BD_v2 §5."""

    PROPOSED = "PROPOSED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ApprovalDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AuditEventType(StrEnum):
    """Known event types. audit_events.event_type is unconstrained varchar,
    but every first-party code path emits one of these for consistency."""

    ACCESS_DENIED = "ACCESS_DENIED"
    LOGIN_SUCCEEDED = "LOGIN_SUCCEEDED"
    LOGIN_FAILED = "LOGIN_FAILED"
    TOKEN_REFRESHED = "TOKEN_REFRESHED"  # noqa: S105 — audit event name, not a secret
    TENANT_CREATED = "TENANT_CREATED"
    SPACE_CREATED = "SPACE_CREATED"
    SPACE_UPDATED = "SPACE_UPDATED"
    SPACE_DELETED = "SPACE_DELETED"
    PROJECT_CREATED = "PROJECT_CREATED"
    PROJECT_DELETED = "PROJECT_DELETED"
    PROJECT_MEMBER_ADDED = "PROJECT_MEMBER_ADDED"
    SPRINT_CREATED = "SPRINT_CREATED"
    SPRINT_UPDATED = "SPRINT_UPDATED"
    SPRINT_COMPLETED = "SPRINT_COMPLETED"
    SOURCE_CONNECTED = "SOURCE_CONNECTED"
    SOURCE_SYNCED = "SOURCE_SYNCED"
    SOURCE_SYNC_FAILED = "SOURCE_SYNC_FAILED"
    SOURCE_DELETED = "SOURCE_DELETED"
    CONNECTOR_REVOKED = "CONNECTOR_REVOKED"
    CONNECTOR_CREATED = "CONNECTOR_CREATED"
    TENANT_MEMBER_ADDED = "TENANT_MEMBER_ADDED"
    MEMBER_ROLE_UPDATED = "MEMBER_ROLE_UPDATED"
    MEMBER_REMOVED = "MEMBER_REMOVED"
    REQUIREMENT_CREATED = "REQUIREMENT_CREATED"
    REQUIREMENT_UPDATED = "REQUIREMENT_UPDATED"
    REQUIREMENT_DELETED = "REQUIREMENT_DELETED"
    REQUIREMENT_COMMENT_ADDED = "REQUIREMENT_COMMENT_ADDED"
    REQUIREMENT_COMMENT_UPDATED = "REQUIREMENT_COMMENT_UPDATED"
    REQUIREMENT_COMMENT_DELETED = "REQUIREMENT_COMMENT_DELETED"
    REPORT_GENERATED = "REPORT_GENERATED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_REJECTED = "DOCUMENT_REJECTED"
    EVIDENCE_SEARCHED = "EVIDENCE_SEARCHED"
    AGENT_RUN_STARTED = "AGENT_RUN_STARTED"
    AGENT_RUN_STEP = "AGENT_RUN_STEP"
    AGENT_RUN_COMPLETED = "AGENT_RUN_COMPLETED"
    AGENT_RUN_FAILED = "AGENT_RUN_FAILED"
    FINDING_CREATED = "FINDING_CREATED"
    ACTION_PROPOSED = "ACTION_PROPOSED"
    ACTION_APPROVED = "ACTION_APPROVED"
    ACTION_REJECTED = "ACTION_REJECTED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    ACTION_EXECUTION_FAILED = "ACTION_EXECUTION_FAILED"
    EXPORT_CREATED = "EXPORT_CREATED"
    RETENTION_TOMBSTONED = "RETENTION_TOMBSTONED"
