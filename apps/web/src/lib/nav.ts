import {
  Activity,
  CheckSquare,
  ClipboardCheck,
  ClipboardList,
  FileSearch,
  FileText,
  LayoutDashboard,
  Plug,
  Settings,
  Sparkles,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

// Deliberately short. The three navigational altitudes in this app are:
//   1. Workspace (this list) — things that cut across every client: your
//      own assigned work, the team roster, the audit trail.
//   2. Space (see `spaceNav` below) — one client, rolled up across all of
//      their projects: findings, evidence, reports, approvals.
//   3. Project (see `projectNav` below) — one engagement's own tools.
// Findings and Approvals also have a workspace-wide, every-client-at-once
// view (reachable from Overview's metric cards, not listed here) because
// "what needs my attention right now, across everyone" is a genuinely
// different question from either a Space or Project rollup answers — but
// Evidence/Reports/Connectors do NOT get a workspace-wide version, since
// "search every client's documents at once" or "a report mixing every
// client together" doesn't answer a real question the way a per-Space or
// per-Project view does.
export const PRIMARY_NAV: NavItem[] = [
  { href: "/app/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/app/project-space", label: "My Work", icon: ClipboardCheck },
  { href: "/app/team", label: "Team", icon: Users },
  { href: "/app/audit", label: "Audit log", icon: Activity },
];

export const SETTINGS_NAV: NavItem = { href: "/app/settings", label: "Settings", icon: Settings };

// A Space rolls up several Projects for one client/initiative. These tabs
// mirror projectNav's shape one level up: instead of "answers about one
// engagement," they answer "how is this whole client doing" by aggregating
// across every project inside the space. Deliberately a shorter list than
// projectNav — no Tasks/Investigations/Connectors/Activity/Settings tab,
// since those are inherently single-project actions (assigning a task,
// running an investigation, managing a connector) rather than something
// that makes sense rolled up across unrelated projects.
export function spaceNav(spaceId: string): NavItem[] {
  return [
    { href: `/app/spaces/${spaceId}`, label: "Overview", icon: LayoutDashboard },
    { href: `/app/spaces/${spaceId}/findings`, label: "Findings", icon: FileText },
    { href: `/app/spaces/${spaceId}/evidence`, label: "Evidence", icon: FileSearch },
    { href: `/app/spaces/${spaceId}/reports`, label: "Reports", icon: FileText },
    { href: `/app/spaces/${spaceId}/approvals`, label: "Approvals", icon: CheckSquare },
  ];
}

export function projectNav(projectId: string): NavItem[] {
  return [
    { href: `/app/projects/${projectId}/overview`, label: "Overview", icon: LayoutDashboard },
    { href: `/app/projects/${projectId}/requirements`, label: "Tasks", icon: ClipboardList },
    { href: `/app/projects/${projectId}/evidence`, label: "Evidence", icon: FileSearch },
    { href: `/app/projects/${projectId}/investigations`, label: "Investigations", icon: Sparkles },
    { href: `/app/projects/${projectId}/findings`, label: "Findings", icon: FileText },
    { href: `/app/projects/${projectId}/approvals`, label: "Approvals", icon: CheckSquare },
    { href: `/app/projects/${projectId}/reports`, label: "Reports", icon: FileText },
    { href: `/app/projects/${projectId}/connectors`, label: "Connectors", icon: Plug },
    { href: `/app/projects/${projectId}/activity`, label: "Activity", icon: Activity },
    { href: `/app/projects/${projectId}/settings`, label: "Settings", icon: Settings },
  ];
}
