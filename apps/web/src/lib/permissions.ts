// Mirrors packages/security/src/atlasai_security/rbac.py — frontend-side
// only for hiding/disabling actions the user could never use. The backend
// remains the sole authority: every one of these checks is re-enforced
// server-side, and a 403 there must always be handled gracefully even if
// the UI thought an action should be allowed.

import type { MembershipRole } from "./types";

export type Permission =
  | "VIEW_PROJECT"
  | "VIEW_INTERNAL_EVIDENCE"
  | "UPLOAD_DOCUMENT"
  | "CONNECT_SOURCE"
  | "SYNC_SOURCE"
  | "RUN_AGENT"
  | "APPROVE_ACTION"
  | "MANAGE_CONNECTORS"
  | "MANAGE_POLICIES"
  | "VIEW_AUDIT_LOG"
  | "MANAGE_PROJECT_MEMBERS"
  | "CREATE_TASK"
  | "EDIT_TASK"
  | "DELETE_TASK"
  | "ASSIGN_TASK"
  | "COMMENT_ON_TASK";

const ALL_PERMISSIONS: Permission[] = [
  "VIEW_PROJECT",
  "VIEW_INTERNAL_EVIDENCE",
  "UPLOAD_DOCUMENT",
  "CONNECT_SOURCE",
  "SYNC_SOURCE",
  "RUN_AGENT",
  "APPROVE_ACTION",
  "MANAGE_CONNECTORS",
  "MANAGE_POLICIES",
  "VIEW_AUDIT_LOG",
  "MANAGE_PROJECT_MEMBERS",
  "CREATE_TASK",
  "EDIT_TASK",
  "DELETE_TASK",
  "ASSIGN_TASK",
  "COMMENT_ON_TASK",
];

// Every role except CLIENT_VIEWER gets full task read/write, ClickUp-style
// — mirrors packages/security/src/atlasai_security/rbac.py exactly.
const TASK_WRITE_PERMISSIONS: Permission[] = ["CREATE_TASK", "EDIT_TASK", "DELETE_TASK", "ASSIGN_TASK", "COMMENT_ON_TASK"];

const ROLE_PERMISSIONS: Record<MembershipRole, Permission[]> = {
  AI_ENGINEER_ADMIN: ALL_PERMISSIONS,
  PROJECT_MANAGER: [
    "VIEW_PROJECT",
    "VIEW_INTERNAL_EVIDENCE",
    "UPLOAD_DOCUMENT",
    "SYNC_SOURCE",
    "RUN_AGENT",
    "APPROVE_ACTION",
    "VIEW_AUDIT_LOG",
    "MANAGE_PROJECT_MEMBERS",
    ...TASK_WRITE_PERMISSIONS,
  ],
  CEO_SALES: ["VIEW_PROJECT", "RUN_AGENT", "VIEW_AUDIT_LOG", ...TASK_WRITE_PERMISSIONS],
  DELIVERY_TEAM: ["VIEW_PROJECT", "VIEW_INTERNAL_EVIDENCE", "UPLOAD_DOCUMENT", "RUN_AGENT", ...TASK_WRITE_PERMISSIONS],
  CLIENT_VIEWER: ["VIEW_PROJECT"],
  WORKER: ["SYNC_SOURCE", "UPLOAD_DOCUMENT", ...TASK_WRITE_PERMISSIONS],
};

export function roleHasPermission(role: MembershipRole | undefined, permission: Permission): boolean {
  if (!role) return false;
  return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
}

export const ROLE_LABELS: Record<MembershipRole, string> = {
  AI_ENGINEER_ADMIN: "Admin",
  PROJECT_MANAGER: "Project Manager",
  CEO_SALES: "Executive",
  DELIVERY_TEAM: "Delivery Team",
  CLIENT_VIEWER: "Client Viewer",
  WORKER: "Worker",
};

export const ALL_ROLES: MembershipRole[] = [
  "AI_ENGINEER_ADMIN",
  "PROJECT_MANAGER",
  "CEO_SALES",
  "DELIVERY_TEAM",
  "CLIENT_VIEWER",
  "WORKER",
];
