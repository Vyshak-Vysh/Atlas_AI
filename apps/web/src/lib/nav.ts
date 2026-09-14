import {
  Activity,
  CheckSquare,
  ClipboardList,
  FileSearch,
  FileText,
  FolderKanban,
  Kanban,
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

export const PRIMARY_NAV: NavItem[] = [
  { href: "/app/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/app/projects", label: "Projects", icon: FolderKanban },
  { href: "/app/project-space", label: "Project Space", icon: Kanban },
  { href: "/app/evidence", label: "Evidence", icon: FileSearch },
  { href: "/app/findings", label: "Findings", icon: Sparkles },
  { href: "/app/approvals", label: "Approvals", icon: CheckSquare },
  { href: "/app/reports", label: "Reports", icon: FileText },
  { href: "/app/connectors", label: "Connectors", icon: Plug },
  { href: "/app/team", label: "Team", icon: Users },
  { href: "/app/audit", label: "Audit log", icon: Activity },
];

export const SETTINGS_NAV: NavItem = { href: "/app/settings", label: "Settings", icon: Settings };

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
