// Central status → { label, className } maps so every list/detail screen
// renders the same badge for the same backend enum value. `className`
// values come from styles/components.css's `.status-*` custom-property
// blocks, applied alongside the generic `.badge.status-badge` pair.

export interface StatusDisplay {
  label: string;
  className: string;
}

const FINDING_STATUS: Record<string, StatusDisplay> = {
  IN_SCOPE_SUPPORTED: { label: "In scope · supported", className: "status-in-scope" },
  OUT_OF_SCOPE_SUPPORTED: { label: "Out of scope · supported", className: "status-out-of-scope" },
  CONFLICTING: { label: "Conflicting", className: "status-conflicting" },
  AMBIGUOUS: { label: "Ambiguous", className: "status-ambiguous" },
  NOT_VERIFIED: { label: "Not verified", className: "status-not-verified" },
  DELIVERED_VERIFIED: { label: "Delivered · verified", className: "status-delivered" },
  PARTIAL: { label: "Partial", className: "status-partial" },
  SUPERSEDED: { label: "Superseded", className: "status-superseded" },
  PENDING_APPROVAL: { label: "Pending approval", className: "status-pending-approval" },
};

const REQUIREMENT_STATUS: Record<string, StatusDisplay> = {
  PROPOSED: { label: "Proposed", className: "status-not-verified" },
  CAPTURED: { label: "Captured", className: "status-not-verified" },
  VALIDATED: { label: "Validated", className: "status-delivered" },
  APPROVED: { label: "Approved", className: "status-in-scope" },
  IN_PROGRESS: { label: "In progress", className: "status-pending-approval" },
  PARTIALLY_DELIVERED: { label: "Partially delivered", className: "status-partial" },
  DELIVERED_VERIFIED: { label: "Delivered · verified", className: "status-delivered" },
  SUPERSEDED: { label: "Superseded", className: "status-superseded" },
  AMBIGUOUS: { label: "Ambiguous", className: "status-ambiguous" },
  CONFLICTING: { label: "Conflicting", className: "status-conflicting" },
  NOT_VERIFIED: { label: "Not verified", className: "status-not-verified" },
  CANCELLED: { label: "Cancelled", className: "status-superseded" },
  REJECTED: { label: "Rejected", className: "status-out-of-scope" },
};

const ACTION_STATUS: Record<string, StatusDisplay> = {
  PROPOSED: { label: "Proposed", className: "status-not-verified" },
  WAITING_APPROVAL: { label: "Waiting for approval", className: "status-pending-approval" },
  APPROVED: { label: "Approved", className: "status-in-scope" },
  EXECUTING: { label: "Executing", className: "status-pending-approval" },
  EXECUTED: { label: "Executed", className: "status-delivered" },
  REJECTED: { label: "Rejected", className: "status-out-of-scope" },
  EXPIRED: { label: "Expired", className: "status-superseded" },
  FAILED: { label: "Failed", className: "status-out-of-scope" },
  CANCELLED: { label: "Cancelled", className: "status-superseded" },
};

const AGENT_RUN_STATUS: Record<string, StatusDisplay> = {
  RECEIVED: { label: "Received", className: "status-not-verified" },
  RUNNING: { label: "Running", className: "status-pending-approval" },
  WAITING_APPROVAL: { label: "Waiting for approval", className: "status-pending-approval" },
  COMPLETED: { label: "Completed", className: "status-delivered" },
  FAILED: { label: "Failed", className: "status-out-of-scope" },
  CANCELLED: { label: "Cancelled", className: "status-superseded" },
};

const CONNECTOR_STATUS: Record<string, StatusDisplay> = {
  ACTIVE: { label: "Connected", className: "status-in-scope" },
  PAUSED: { label: "Paused", className: "status-partial" },
  REVOKED: { label: "Revoked", className: "status-superseded" },
  ERROR: { label: "Error", className: "status-out-of-scope" },
};

const PROJECT_STATUS: Record<string, StatusDisplay> = {
  ACTIVE: { label: "Active", className: "status-in-scope" },
  ON_HOLD: { label: "On hold", className: "status-partial" },
  COMPLETED: { label: "Completed", className: "status-delivered" },
  ARCHIVED: { label: "Archived", className: "status-superseded" },
};

const PHASE_STATUS: Record<string, StatusDisplay> = {
  PLANNED: { label: "Planned", className: "status-not-verified" },
  IN_PROGRESS: { label: "In progress", className: "status-pending-approval" },
  COMPLETED: { label: "Completed", className: "status-delivered" },
  CANCELLED: { label: "Cancelled", className: "status-superseded" },
};

const SPACE_STATUS: Record<string, StatusDisplay> = {
  ACTIVE: { label: "Active", className: "status-in-scope" },
  ON_HOLD: { label: "On hold", className: "status-partial" },
  ARCHIVED: { label: "Archived", className: "status-superseded" },
};

const SPRINT_STATUS: Record<string, StatusDisplay> = {
  PLANNED: { label: "Planned", className: "status-not-verified" },
  ACTIVE: { label: "Active", className: "status-pending-approval" },
  COMPLETED: { label: "Completed", className: "status-delivered" },
  CANCELLED: { label: "Cancelled", className: "status-superseded" },
};

// Day-to-day task board state — a separate axis from REQUIREMENT_STATUS
// above (evidence-verification lifecycle). Keep these two displays
// visually distinct wherever both appear (see the requirements list page).
const TASK_STATUS: Record<string, StatusDisplay> = {
  TO_DO: { label: "To do", className: "status-not-verified" },
  IN_PROGRESS: { label: "In progress", className: "status-pending-approval" },
  IN_REVIEW: { label: "In review", className: "status-ambiguous" },
  DONE: { label: "Done", className: "status-in-scope" },
  BLOCKED: { label: "Blocked", className: "status-out-of-scope" },
};

export const TASK_STATUS_COLUMNS: { value: string; label: string }[] = [
  { value: "TO_DO", label: "To do" },
  { value: "IN_PROGRESS", label: "In progress" },
  { value: "IN_REVIEW", label: "In review" },
  { value: "DONE", label: "Done" },
  { value: "BLOCKED", label: "Blocked" },
];

const TASK_PRIORITY: Record<string, { label: string; variant: "danger" | "warning" | "info" | "neutral" }> = {
  URGENT: { label: "Urgent", variant: "danger" },
  HIGH: { label: "High", variant: "warning" },
  NORMAL: { label: "Normal", variant: "info" },
  LOW: { label: "Low", variant: "neutral" },
};

export const TASK_PRIORITIES = ["URGENT", "HIGH", "NORMAL", "LOW"] as const;

export function taskStatusDisplay(value: string): StatusDisplay {
  return lookup(TASK_STATUS, value);
}

export function taskPriorityDisplay(value: string): { label: string; variant: "danger" | "warning" | "info" | "neutral" } {
  return TASK_PRIORITY[value] ?? { label: value.replaceAll("_", " "), variant: "neutral" };
}

function lookup(map: Record<string, StatusDisplay>, value: string): StatusDisplay {
  return map[value] ?? { label: value.replaceAll("_", " "), className: "status-not-verified" };
}

export const findingStatusDisplay = (value: string): StatusDisplay => lookup(FINDING_STATUS, value);
export const requirementStatusDisplay = (value: string): StatusDisplay => lookup(REQUIREMENT_STATUS, value);
export const actionStatusDisplay = (value: string): StatusDisplay => lookup(ACTION_STATUS, value);
export const agentRunStatusDisplay = (value: string): StatusDisplay => lookup(AGENT_RUN_STATUS, value);
export const connectorStatusDisplay = (value: string): StatusDisplay => lookup(CONNECTOR_STATUS, value);
export const projectStatusDisplay = (value: string): StatusDisplay => lookup(PROJECT_STATUS, value);
export const phaseStatusDisplay = (value: string): StatusDisplay => lookup(PHASE_STATUS, value);
export const spaceStatusDisplay = (value: string): StatusDisplay => lookup(SPACE_STATUS, value);
export const sprintStatusDisplay = (value: string): StatusDisplay => lookup(SPRINT_STATUS, value);

export const FINDING_TYPE_LABELS: Record<string, string> = {
  IN_SCOPE_SUPPORTED: "In scope",
  OUT_OF_SCOPE_SUPPORTED: "Out of scope",
  CONFLICTING: "Evidence conflict",
  AMBIGUOUS: "Requirement ambiguity",
  NOT_VERIFIED: "Not verified",
  DELIVERED_VERIFIED: "Delivery mismatch resolved",
  PARTIAL: "Partial delivery",
  SUPERSEDED: "Superseded",
  PENDING_APPROVAL: "Pending approval",
};

export const AGENT_STATE_LABELS: Record<string, string> = {
  RECEIVED: "Received",
  CLASSIFY: "Classifying question",
  PLAN: "Planning retrieval",
  RETRIEVE: "Searching evidence",
  RERANK: "Ranking evidence",
  ANALYZE: "Analyzing",
  VERIFY: "Verifying citations",
  FINDING: "Preparing finding",
  ACTION_DECISION: "Deciding on next action",
  PROPOSE_ACTION: "Proposing action",
  WAIT_APPROVAL: "Waiting for approval",
  EXECUTE: "Executing",
  COMPLETE: "Complete",
  RETRY: "Retrying",
  FAILED: "Failed",
};

export const AGENT_STEP_ORDER = [
  "RECEIVED",
  "CLASSIFY",
  "PLAN",
  "RETRIEVE",
  "RERANK",
  "ANALYZE",
  "VERIFY",
  "FINDING",
  "COMPLETE",
];
