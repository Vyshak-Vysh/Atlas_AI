// Mirrors of apps/api's Pydantic response schemas. Hand-written rather than
// codegen'd from the OpenAPI schema — see apps/api/src/atlasai_api/schemas/*
// for the source of truth. Status/enum fields are typed as string-literal
// unions for editor support, but the backend columns are unconstrained
// varchar, so always fall back to displaying the raw string for an unknown
// value rather than assuming exhaustiveness.

// ---------------------------------------------------------------------------
// Enums (packages/domain/src/atlasai_domain/enums.py)
// ---------------------------------------------------------------------------

export type MembershipRole =
  | "PROJECT_MANAGER"
  | "AI_ENGINEER_ADMIN"
  | "CEO_SALES"
  | "DELIVERY_TEAM"
  | "CLIENT_VIEWER"
  | "WORKER";

export type ProjectStatus = "ACTIVE" | "ON_HOLD" | "COMPLETED" | "ARCHIVED";
export type PhaseStatus = "PLANNED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";

export type ConnectorProvider =
  | "MANUAL_UPLOAD"
  | "GIT_CI_GITHUB"
  | "GMAIL"
  | "MSGRAPH"
  | "GOOGLE_DRIVE"
  | "MEETINGS"
  | "PM_JIRA";

export type ConnectorStatus = "ACTIVE" | "PAUSED" | "REVOKED" | "ERROR";
export type SourceVisibility = "PROJECT" | "INTERNAL" | "CLIENT_SHARED";
export type SyncRunStatus = "RUNNING" | "SUCCEEDED" | "FAILED" | "PARTIAL";

export type RequirementStatus =
  | "PROPOSED"
  | "CAPTURED"
  | "VALIDATED"
  | "APPROVED"
  | "IN_PROGRESS"
  | "PARTIALLY_DELIVERED"
  | "DELIVERED_VERIFIED"
  | "SUPERSEDED"
  | "AMBIGUOUS"
  | "CONFLICTING"
  | "NOT_VERIFIED"
  | "CANCELLED"
  | "REJECTED";

export type AgentRunStatus = "RECEIVED" | "RUNNING" | "WAITING_APPROVAL" | "COMPLETED" | "FAILED" | "CANCELLED";

export type FindingStatus =
  | "IN_SCOPE_SUPPORTED"
  | "OUT_OF_SCOPE_SUPPORTED"
  | "CONFLICTING"
  | "AMBIGUOUS"
  | "NOT_VERIFIED"
  | "DELIVERED_VERIFIED"
  | "PARTIAL"
  | "SUPERSEDED"
  | "PENDING_APPROVAL";

export type ActionType = "DRAFT_CLIENT_RESPONSE" | "CREATE_REVIEW_TASK" | "EXPORT_REPORT" | "SEND_EMAIL";

export type ActionStatus =
  | "PROPOSED"
  | "WAITING_APPROVAL"
  | "APPROVED"
  | "EXECUTING"
  | "EXECUTED"
  | "REJECTED"
  | "EXPIRED"
  | "FAILED"
  | "CANCELLED";

export type AgentStateName =
  | "RECEIVED"
  | "CLASSIFY"
  | "PLAN"
  | "RETRIEVE"
  | "RERANK"
  | "ANALYZE"
  | "VERIFY"
  | "FINDING"
  | "ACTION_DECISION"
  | "PROPOSE_ACTION"
  | "WAIT_APPROVAL"
  | "EXECUTE"
  | "COMPLETE"
  | "RETRY"
  | "FAILED";

// ---------------------------------------------------------------------------
// Auth / users / tenants
// ---------------------------------------------------------------------------

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  tenant_id: string | null;
}

export interface UserResponse {
  id: string;
  email: string;
  display_name: string;
  status: string;
  created_at: string;
}

export interface MyTenantMembershipResponse {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  role: string;
}

export interface TenantResponse {
  id: string;
  name: string;
  slug: string;
  status: string;
  created_at: string;
}

export interface TenantMemberDetailResponse {
  tenant_id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  joined_at: string;
}

// ---------------------------------------------------------------------------
// Projects / phases / members
// ---------------------------------------------------------------------------

export interface ProjectResponse {
  id: string;
  tenant_id: string;
  name: string;
  client_name: string | null;
  code: string | null;
  status: string;
  timezone: string;
  created_at: string;
}

export interface PhaseResponse {
  id: string;
  project_id: string;
  name: string;
  phase_number: number;
  start_date: string | null;
  end_date: string | null;
  status: string;
}

export interface ProjectOverviewResponse {
  project: ProjectResponse;
  phases: PhaseResponse[];
  member_count: number;
}

export interface ProjectMemberDetailResponse {
  project_id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  joined_at: string;
}

// ---------------------------------------------------------------------------
// Sources / documents / evidence
// ---------------------------------------------------------------------------

export interface DocumentUploadResponse {
  source_record_id: string;
  source_version_id: string;
  content_hash: string;
  status: string;
}

export interface SourceRecordResponse {
  id: string;
  external_id: string;
  record_type: string;
  title: string | null;
  canonical_url: string | null;
  current_version_id: string | null;
  visibility: string;
  deleted_at: string | null;
  created_at: string;
  ingestion_status: "READY" | "PROCESSING";
}

export interface EvidenceLocation {
  page_number: number | null;
  section_path: string | null;
  sheet_name: string | null;
  cell_range: string | null;
  speaker: string | null;
  start_ms: number | null;
  end_ms: number | null;
}

export interface EvidenceTimestamps {
  authored_at: string | null;
  modified_at: string | null;
  imported_at: string | null;
  meeting_at: string | null;
  effective_at: string | null;
}

export interface EvidenceCandidate {
  evidence_chunk_id: string;
  source_record_id: string;
  source_version_id: string;
  content: string;
  lexical_score: number | null;
  vector_score: number | null;
  rerank_score: number | null;
  location: EvidenceLocation;
  timestamps: EvidenceTimestamps;
  requirement_ids: string[];
  visibility: string;
  metadata: Record<string, unknown>;
}

export interface EvidenceSearchResponse {
  query: string;
  results: EvidenceCandidate[];
}

// ---------------------------------------------------------------------------
// Agent runs / investigations
// ---------------------------------------------------------------------------

export interface AgentRunResponse {
  id: string;
  project_id: string;
  question: string;
  status: string;
  finding_id: string | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface AgentStepEvent {
  step_no: number;
  state_name: string;
  status: string;
  tool_name: string | null;
}

// ---------------------------------------------------------------------------
// Findings
// ---------------------------------------------------------------------------

export interface FindingCitationResponse {
  evidence_chunk_id: string;
  citation_label: string | null;
  quote: string;
  location: Partial<EvidenceLocation>;
}

export interface ContradictionEntry {
  side_a_summary?: string;
  side_a_citation?: string;
  side_b_summary?: string;
  side_b_citation?: string;
  why_it_matters?: string;
}

export interface MissingEvidenceEntry {
  what_was_searched?: string;
  what_was_unavailable?: string;
  what_would_resolve_it?: string;
}

export interface FindingResponse {
  id: string;
  agent_run_id: string;
  project_id: string;
  status: string;
  summary: string;
  facts: unknown[];
  inferences: unknown[];
  conflicts: ContradictionEntry[];
  missing_evidence: MissingEvidenceEntry[];
  confidence: number | null;
  requires_human_review: boolean;
  citations: FindingCitationResponse[];
  created_at: string;
}

// ---------------------------------------------------------------------------
// Actions / approvals
// ---------------------------------------------------------------------------

export interface ActionResponse {
  id: string;
  project_id: string;
  action_type: string;
  payload_json: Record<string, unknown>;
  status: string;
  payload_hash: string;
  created_at: string;
  executed_at: string | null;
}

// ---------------------------------------------------------------------------
// Connectors
// ---------------------------------------------------------------------------

export interface ConnectorResponse {
  id: string;
  provider: string;
  status: string;
  external_account_id: string | null;
  scopes: Record<string, unknown>;
  last_sync_at: string | null;
  created_at: string;
}

export interface ConnectorProviderInfo {
  provider: string;
  display_name: string;
  is_available: boolean;
  connector: ConnectorResponse | null;
}

export interface SyncRunResponse {
  id: string;
  connector_id: string;
  status: string;
  cursor_before: string | null;
  cursor_after: string | null;
  started_at: string;
  finished_at: string | null;
  items_seen: number;
  items_changed: number;
  error_json: Record<string, unknown> | null;
}

// ---------------------------------------------------------------------------
// Requirements
// ---------------------------------------------------------------------------

export interface RequirementResponse {
  id: string;
  project_id: string;
  phase_id: string | null;
  key: string;
  title: string;
  description: string | null;
  status: string;
  acceptance_criteria: unknown[];
  created_at: string;
  updated_at: string;
}

export interface RequirementEvidenceLinkResponse {
  evidence_chunk_id: string;
  relation_type: string;
  confidence: number | null;
  rationale: string | null;
}

export interface DeliveryRecordResponse {
  id: string;
  requirement_id: string;
  status: string;
  source_record_id: string | null;
  evidence_summary: string | null;
  verified_by: string | null;
  verified_at: string | null;
  created_at: string;
}

export interface RequirementDetailResponse {
  requirement: RequirementResponse;
  evidence_links: RequirementEvidenceLinkResponse[];
  delivery_records: DeliveryRecordResponse[];
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

export interface PhaseProgress {
  phase: PhaseResponse;
  requirement_count: number;
  requirements_delivered: number;
}

export interface FindingStatusCount {
  status: string;
  count: number;
}

export interface ProjectReportResponse {
  project: ProjectResponse;
  generated_at: string;
  phase_progress: PhaseProgress[];
  total_requirements: number;
  total_sources: number;
  latest_source_at: string | null;
  total_findings: number;
  findings_by_status: FindingStatusCount[];
  recent_findings: FindingResponse[];
  pending_approvals: number;
  member_count: number;
}

// ---------------------------------------------------------------------------
// Audit
// ---------------------------------------------------------------------------

export interface AuditEventResponse {
  id: string;
  actor_id: string | null;
  event_type: string;
  target_type: string | null;
  target_id: string | null;
  request_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}
