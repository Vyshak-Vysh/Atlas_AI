import { clearSession, loadSession, updateAccessToken } from "./auth-storage";
import type {
  ActionResponse,
  AgentRunResponse,
  AuditEventResponse,
  ConnectorProviderInfo,
  ConnectorResponse,
  DocumentUploadResponse,
  EvidenceSearchResponse,
  FindingResponse,
  MyTenantMembershipResponse,
  PhaseResponse,
  ProjectMemberDetailResponse,
  ProjectOverviewResponse,
  ProjectReportResponse,
  ProjectResponse,
  RequirementDetailResponse,
  RequirementResponse,
  SourceRecordResponse,
  SyncRunResponse,
  TenantMemberDetailResponse,
  TenantResponse,
  TokenResponse,
  UserResponse,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `API error ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const session = loadSession();
  if (!session) return null;

  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: session.refreshToken }),
      });
      if (!response.ok) {
        clearSession();
        return null;
      }
      const body: TokenResponse = await response.json();
      updateAccessToken(body.access_token, body.refresh_token);
      return body.access_token;
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

interface RequestOptions {
  method?: string;
  json?: unknown;
  form?: FormData;
  query?: Record<string, string | number | undefined>;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const session = loadSession();
  const url = new URL(`${API_BASE_URL}${path}`);
  if (options.query) {
    for (const [key, value] of Object.entries(options.query)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }

  const doFetch = async (accessToken: string | undefined): Promise<Response> => {
    const headers: Record<string, string> = {};
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    let body: BodyInit | undefined;
    if (options.form) {
      body = options.form;
    } else if (options.json !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.json);
    }
    return fetch(url.toString(), { method: options.method ?? "GET", headers, body });
  };

  let response = await doFetch(session?.accessToken);

  if (response.status === 401 && session) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      response = await doFetch(newToken);
    }
  }

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = (await response.json()).detail;
    } catch {
      detail = await response.text();
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  // --- Auth --------------------------------------------------------------
  register: (body: { tenant_name: string; email: string; password: string; display_name: string }) =>
    request<TokenResponse>("/api/v1/auth/register", { method: "POST", json: body }),

  login: (body: { email: string; password: string }) =>
    request<TokenResponse>("/api/v1/auth/login", { method: "POST", json: body }),

  logout: (refreshToken: string) =>
    request<void>("/api/v1/auth/logout", { method: "POST", json: { refresh_token: refreshToken } }),

  switchTenant: (tenantId: string) =>
    request<TokenResponse>("/api/v1/auth/switch-tenant", { method: "POST", json: { tenant_id: tenantId } }),

  // --- Users ---------------------------------------------------------------
  getMe: () => request<UserResponse>("/api/v1/users/me"),

  updateMe: (body: { display_name: string }) =>
    request<UserResponse>("/api/v1/users/me", { method: "PATCH", json: body }),

  listMyTenants: () => request<MyTenantMembershipResponse[]>("/api/v1/users/me/tenants"),

  // --- Tenants / team ------------------------------------------------------
  getTenant: (tenantId: string) => request<TenantResponse>(`/api/v1/tenants/${tenantId}`),

  listTenantMembers: (tenantId: string) =>
    request<TenantMemberDetailResponse[]>(`/api/v1/tenants/${tenantId}/members`),

  addTenantMember: (tenantId: string, body: { email: string; role: string }) =>
    request<TenantMemberDetailResponse>(`/api/v1/tenants/${tenantId}/members`, { method: "POST", json: body }),

  updateTenantMemberRole: (tenantId: string, userId: string, role: string) =>
    request<void>(`/api/v1/tenants/${tenantId}/members/${userId}`, { method: "PATCH", json: { role } }),

  removeTenantMember: (tenantId: string, userId: string) =>
    request<void>(`/api/v1/tenants/${tenantId}/members/${userId}`, { method: "DELETE" }),

  // --- Projects --------------------------------------------------------------
  listProjects: (tenantId: string) =>
    request<ProjectResponse[]>("/api/v1/projects", { query: { tenant_id: tenantId } }),

  createProject: (body: { tenant_id: string; name: string; client_name?: string; code?: string }) =>
    request<ProjectResponse>("/api/v1/projects", { method: "POST", json: body }),

  updateProject: (projectId: string, body: { name?: string; client_name?: string; status?: string }) =>
    request<ProjectResponse>(`/api/v1/projects/${projectId}`, { method: "PATCH", json: body }),

  getProjectOverview: (projectId: string) =>
    request<ProjectOverviewResponse>(`/api/v1/projects/${projectId}/overview`),

  createPhase: (
    projectId: string,
    body: { name: string; phase_number: number; start_date?: string; end_date?: string },
  ) => request<PhaseResponse>(`/api/v1/projects/${projectId}/phases`, { method: "POST", json: body }),

  listProjectMembers: (projectId: string) =>
    request<ProjectMemberDetailResponse[]>(`/api/v1/projects/${projectId}/members`),

  addProjectMember: (projectId: string, body: { email: string; role: string }) =>
    request<ProjectMemberDetailResponse>(`/api/v1/projects/${projectId}/members`, { method: "POST", json: body }),

  updateProjectMemberRole: (projectId: string, userId: string, role: string) =>
    request<void>(`/api/v1/projects/${projectId}/members/${userId}`, { method: "PATCH", json: { role } }),

  removeProjectMember: (projectId: string, userId: string) =>
    request<void>(`/api/v1/projects/${projectId}/members/${userId}`, { method: "DELETE" }),

  getProjectReport: (projectId: string) => request<ProjectReportResponse>(`/api/v1/projects/${projectId}/report`),

  // --- Documents / sources -----------------------------------------------
  uploadDocument: (projectId: string, file: File, visibility = "PROJECT") => {
    const form = new FormData();
    form.append("project_id", projectId);
    form.append("visibility", visibility);
    form.append("file", file);
    return request<DocumentUploadResponse>("/api/v1/documents/upload", { method: "POST", form });
  },

  listSources: (projectId: string, limit = 100, offset = 0) =>
    request<SourceRecordResponse[]>("/api/v1/sources", { query: { project_id: projectId, limit, offset } }),

  getSource: (sourceId: string, projectId: string) =>
    request<SourceRecordResponse>(`/api/v1/sources/${sourceId}`, { query: { project_id: projectId } }),

  deleteSource: (sourceId: string, projectId: string) =>
    request<void>(`/api/v1/sources/${sourceId}`, { method: "DELETE", query: { project_id: projectId } }),

  // --- Evidence --------------------------------------------------------------
  searchEvidence: (projectId: string, q: string, topN = 10) =>
    request<EvidenceSearchResponse>("/api/v1/evidence/search", {
      query: { project_id: projectId, q, top_n: topN },
    }),

  // --- Agent runs / investigations -----------------------------------------
  createAgentRun: (projectId: string, question: string) =>
    request<AgentRunResponse>("/api/v1/agent/runs", {
      method: "POST",
      query: { project_id: projectId },
      json: { project_id: projectId, question },
    }),

  getAgentRun: (runId: string, projectId: string) =>
    request<AgentRunResponse>(`/api/v1/agent/runs/${runId}`, { query: { project_id: projectId } }),

  listAgentRuns: (projectId: string, limit = 100, offset = 0) =>
    request<AgentRunResponse[]>("/api/v1/agent/runs", { query: { project_id: projectId, limit, offset } }),

  agentRunEventsUrl: (runId: string, projectId: string) =>
    `${API_BASE_URL}/api/v1/agent/runs/${runId}/events?project_id=${projectId}`,

  // --- Findings --------------------------------------------------------------
  listFindings: (projectId: string, status?: string, limit = 100, offset = 0) =>
    request<FindingResponse[]>("/api/v1/findings", { query: { project_id: projectId, status, limit, offset } }),

  getFinding: (findingId: string, projectId: string) =>
    request<FindingResponse>(`/api/v1/findings/${findingId}`, { query: { project_id: projectId } }),

  // --- Actions / approvals -----------------------------------------------
  listActions: (projectId: string, status?: string, limit = 100, offset = 0) =>
    request<ActionResponse[]>("/api/v1/actions", { query: { project_id: projectId, status, limit, offset } }),

  getAction: (actionId: string, projectId: string) =>
    request<ActionResponse>(`/api/v1/actions/${actionId}`, { query: { project_id: projectId } }),

  approveAction: (actionId: string, projectId: string, body: { reason?: string; expected_payload_hash?: string }) =>
    request<ActionResponse>(`/api/v1/actions/${actionId}/approve`, {
      method: "POST",
      query: { project_id: projectId },
      json: body,
    }),

  rejectAction: (actionId: string, projectId: string, body: { reason?: string }) =>
    request<ActionResponse>(`/api/v1/actions/${actionId}/reject`, {
      method: "POST",
      query: { project_id: projectId },
      json: body,
    }),

  // --- Connectors --------------------------------------------------------------
  listConnectors: (projectId: string) =>
    request<ConnectorProviderInfo[]>("/api/v1/connectors", { query: { project_id: projectId } }),

  createConnector: (body: { tenant_id: string; project_id: string; provider: string; external_account_id?: string }) =>
    request<ConnectorResponse>("/api/v1/connectors", { method: "POST", json: body }),

  listSyncRuns: (connectorId: string, projectId: string) =>
    request<SyncRunResponse[]>(`/api/v1/connectors/${connectorId}/sync-runs`, { query: { project_id: projectId } }),

  revokeConnector: (connectorId: string, projectId: string) =>
    request<ConnectorResponse>(`/api/v1/connectors/${connectorId}`, {
      method: "DELETE",
      query: { project_id: projectId },
    }),

  // --- Requirements --------------------------------------------------------
  listRequirements: (projectId: string, status?: string, phaseId?: string) =>
    request<RequirementResponse[]>("/api/v1/requirements", {
      query: { project_id: projectId, status, phase_id: phaseId },
    }),

  createRequirement: (
    projectId: string,
    body: { key: string; title: string; status: string; phase_id?: string; description?: string },
  ) =>
    request<RequirementResponse>("/api/v1/requirements", {
      method: "POST",
      query: { project_id: projectId },
      json: body,
    }),

  getRequirement: (requirementId: string, projectId: string) =>
    request<RequirementDetailResponse>(`/api/v1/requirements/${requirementId}`, {
      query: { project_id: projectId },
    }),

  // --- Audit ------------------------------------------------------------------
  listAuditEvents: (tenantId: string, limit = 100, offset = 0) =>
    request<AuditEventResponse[]>("/api/v1/audit-events", { query: { tenant_id: tenantId, limit, offset } }),
};

export { API_BASE_URL };
