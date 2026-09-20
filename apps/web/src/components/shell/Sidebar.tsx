"use client";

import { ChevronDown, ChevronLeft, ChevronRight, ChevronsUpDown, Plus } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useProjects } from "@/hooks/useProjects";
import { useCurrentTenant, useMyTenants } from "@/hooks/useCurrentWorkspace";
import { useSpaces } from "@/hooks/useSpaces";
import { useAuth } from "@/lib/auth-context";
import { initials } from "@/lib/format";
import { PRIMARY_NAV, SETTINGS_NAV, projectNav, type NavItem } from "@/lib/nav";
import type { ProjectResponse, SpaceResponse } from "@/lib/types";
import { useUiStore } from "@/store/ui";
import { CreateSpaceDialog } from "@/components/spaces/CreateSpaceDialog";
import { DropdownMenu, MenuItem, MenuSeparator } from "@/components/ui/DropdownMenu";
import { Tooltip } from "@/components/ui/Tooltip";

function useProjectIdFromPath(pathname: string): string | undefined {
  const match = pathname.match(/^\/app\/projects\/([0-9a-f-]{8,})/i);
  return match?.[1];
}

function useSpaceIdFromPath(pathname: string): string | undefined {
  const match = pathname.match(/^\/app\/spaces\/([0-9a-f-]{8,})/i);
  return match?.[1];
}

/**
 * Single unified nav tree — Spaces expand to reveal their Projects, Projects
 * expand to reveal their own tools (Tasks, Evidence, ...) — rather than the
 * old design of swapping between three unrelated flat nav lists depending on
 * which URL you were on. Modeled on ClickUp/Notion/Slack's persistent
 * sidebar tree: you can always see which Space a Project lives in and what
 * you can do inside it at the same time.
 */
export function Sidebar() {
  const pathname = usePathname();
  const activeProjectId = useProjectIdFromPath(pathname);
  const activeSpaceId = useSpaceIdFromPath(pathname);
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const mobileOpen = useUiStore((s) => s.mobileNavOpen);
  const setMobileOpen = useUiStore((s) => s.setMobileNavOpen);
  const expandedNavIds = useUiStore((s) => s.expandedNavIds);
  const toggleNavExpanded = useUiStore((s) => s.toggleNavExpanded);
  const expandNavIds = useUiStore((s) => s.expandNavIds);
  const { switchTenant } = useAuth();

  const { data: tenant } = useCurrentTenant();
  const { data: tenants } = useMyTenants();
  const { data: spaces } = useSpaces();
  const { data: projects } = useProjects();

  const [showCreateSpace, setShowCreateSpace] = useState(false);

  // Deep-linking into a project or space (dashboard shortcut, search
  // result, bookmark) should reveal its branch, not leave the tree
  // collapsed and looking like that project has vanished from its space.
  useEffect(() => {
    if (!projects) return;
    const ids: string[] = [];
    if (activeSpaceId) ids.push(`space:${activeSpaceId}`);
    if (activeProjectId) {
      ids.push(`project:${activeProjectId}`);
      const project = projects.find((p) => p.id === activeProjectId);
      if (project?.space_id) ids.push(`space:${project.space_id}`);
      else if (project) ids.push("ungrouped");
    }
    if (ids.length > 0) expandNavIds(ids);
    // Only re-run when the active route or project list changes — expandNavIds is stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProjectId, activeSpaceId, projects]);

  const isExpanded = (id: string) => expandedNavIds.includes(id);

  const projectsBySpace = new Map<string, ProjectResponse[]>();
  const ungrouped: ProjectResponse[] = [];
  for (const project of projects ?? []) {
    if (project.space_id) {
      const list = projectsBySpace.get(project.space_id) ?? [];
      list.push(project);
      projectsBySpace.set(project.space_id, list);
    } else {
      ungrouped.push(project);
    }
  }

  return (
    <aside className="app-sidebar" data-mobile-open={mobileOpen} aria-label="Primary">
      <Link href="/app/overview" className="sidebar-brand">
        <span className="sidebar-brand__mark">A</span>
        <span className="sidebar-brand__name">AtlasAI</span>
      </Link>

      <div style={{ padding: "0 var(--space-3)" }}>
        <WorkspaceSwitcherMenu
          tenantName={tenant?.name}
          tenants={tenants}
          currentTenantId={tenant?.id}
          onSwitch={switchTenant}
          collapsed={collapsed}
        />
      </div>

      <p className="sidebar-section-label">Workspace</p>
      <nav className="sidebar-nav">
        {PRIMARY_NAV.map((item) => (
          <SidebarLeaf key={item.href} item={item} pathname={pathname} />
        ))}
      </nav>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Link
          href="/app/spaces"
          className="sidebar-section-label sidebar-section-label--link"
          aria-current={pathname === "/app/spaces" ? "page" : undefined}
          title="Browse all spaces"
        >
          Spaces
        </Link>
        {!collapsed && (
          <button
            type="button"
            className="sidebar-tree-add-btn sidebar-tree-add-btn--visible"
            onClick={() => setShowCreateSpace(true)}
            aria-label="New space"
            title="New space"
          >
            <Plus size={14} aria-hidden />
          </button>
        )}
      </div>

      <nav className="sidebar-nav">
        {(spaces ?? []).map((space) => (
          <SpaceBranch
            key={space.id}
            space={space}
            projects={projectsBySpace.get(space.id) ?? []}
            pathname={pathname}
            collapsed={collapsed}
            isExpanded={isExpanded}
            onToggle={toggleNavExpanded}
          />
        ))}
        {ungrouped.length > 0 && !collapsed && (
          <UngroupedBranch projects={ungrouped} pathname={pathname} isExpanded={isExpanded} onToggle={toggleNavExpanded} />
        )}
        {(spaces ?? []).length === 0 && ungrouped.length === 0 && !collapsed && (
          <p style={{ padding: "0 var(--space-5)", fontSize: "var(--font-size-xs)", color: "rgba(255,255,255,0.4)" }}>
            No spaces yet
          </p>
        )}
      </nav>

      <div className="sidebar-footer">
        <nav className="sidebar-nav" style={{ padding: 0, marginBottom: "var(--space-2)" }}>
          <SidebarLeaf item={SETTINGS_NAV} pathname={pathname} />
        </nav>
        <Tooltip label={collapsed ? "Expand sidebar" : "Collapse sidebar"} side="top">
          <button
            type="button"
            className="sidebar-collapse-btn"
            onClick={() => {
              toggleSidebar();
              setMobileOpen(false);
            }}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight size={16} aria-hidden /> : <ChevronLeft size={16} aria-hidden />}
          </button>
        </Tooltip>
      </div>

      <CreateSpaceDialog open={showCreateSpace} onClose={() => setShowCreateSpace(false)} />
    </aside>
  );
}

function SidebarLeaf({ item, pathname, depth = 0 }: { item: NavItem; pathname: string; depth?: number }) {
  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className="sidebar-link"
      aria-current={active ? "page" : undefined}
      style={depth > 0 ? { paddingLeft: `calc(var(--space-3) + ${depth * 1.1}rem)` } : undefined}
    >
      <Icon size={depth > 0 ? 15 : 17} aria-hidden />
      <span className="sidebar-link__label">{item.label}</span>
    </Link>
  );
}

function SpaceBranch({
  space,
  projects,
  pathname,
  collapsed,
  isExpanded,
  onToggle,
}: {
  space: SpaceResponse;
  projects: ProjectResponse[];
  pathname: string;
  collapsed: boolean;
  isExpanded: (id: string) => boolean;
  onToggle: (id: string) => void;
}) {
  const key = `space:${space.id}`;
  const expanded = isExpanded(key);
  const href = `/app/spaces/${space.id}`;
  const active = pathname === href;
  const dotColor = space.color ?? "var(--color-brand-500)";

  if (collapsed) {
    return (
      <Link href={href} className="sidebar-link" aria-current={active ? "page" : undefined} title={space.name}>
        <span className="sidebar-tree-dot" style={{ background: dotColor }} aria-hidden />
      </Link>
    );
  }

  return (
    <div>
      <div className="sidebar-tree-row">
        <button
          type="button"
          className="sidebar-tree-toggle"
          data-expanded={expanded}
          onClick={() => onToggle(key)}
          aria-label={expanded ? `Collapse ${space.name}` : `Expand ${space.name}`}
        >
          <ChevronDown size={14} aria-hidden />
        </button>
        <Link href={href} className="sidebar-link" aria-current={active ? "page" : undefined} style={{ flex: 1 }}>
          <span className="sidebar-tree-dot" style={{ background: dotColor }} aria-hidden />
          <span className="sidebar-link__label">{space.name}</span>
        </Link>
        <Link
          href={`/app/projects/new?spaceId=${space.id}`}
          className="sidebar-tree-add-btn"
          aria-label={`New project in ${space.name}`}
          title={`New project in ${space.name}`}
        >
          <Plus size={13} aria-hidden />
        </Link>
      </div>
      {expanded &&
        (projects.length > 0 ? (
          projects.map((project) => (
            <ProjectBranch key={project.id} project={project} pathname={pathname} isExpanded={isExpanded} onToggle={onToggle} />
          ))
        ) : (
          <p className="sidebar-tree-empty">No projects yet</p>
        ))}
    </div>
  );
}

function UngroupedBranch({
  projects,
  pathname,
  isExpanded,
  onToggle,
}: {
  projects: ProjectResponse[];
  pathname: string;
  isExpanded: (id: string) => boolean;
  onToggle: (id: string) => void;
}) {
  const key = "ungrouped";
  const expanded = isExpanded(key);

  return (
    <div>
      <div className="sidebar-tree-row">
        <button
          type="button"
          className="sidebar-tree-toggle"
          data-expanded={expanded}
          onClick={() => onToggle(key)}
          aria-label={expanded ? "Collapse projects with no space" : "Expand projects with no space"}
        >
          <ChevronDown size={14} aria-hidden />
        </button>
        <span className="sidebar-link" style={{ flex: 1, cursor: "default" }}>
          <span className="sidebar-tree-dot sidebar-tree-dot--empty" aria-hidden />
          <span className="sidebar-link__label">No space</span>
        </span>
        <Link href="/app/projects/new" className="sidebar-tree-add-btn" aria-label="New project" title="New project">
          <Plus size={13} aria-hidden />
        </Link>
      </div>
      {expanded &&
        projects.map((project) => (
          <ProjectBranch key={project.id} project={project} pathname={pathname} isExpanded={isExpanded} onToggle={onToggle} />
        ))}
    </div>
  );
}

function ProjectBranch({
  project,
  pathname,
  isExpanded,
  onToggle,
}: {
  project: ProjectResponse;
  pathname: string;
  isExpanded: (id: string) => boolean;
  onToggle: (id: string) => void;
}) {
  const key = `project:${project.id}`;
  const expanded = isExpanded(key);
  const href = `/app/projects/${project.id}/overview`;

  return (
    <div>
      <div className="sidebar-tree-row" data-depth="1">
        <button
          type="button"
          className="sidebar-tree-toggle"
          data-expanded={expanded}
          onClick={() => onToggle(key)}
          aria-label={expanded ? `Collapse ${project.name}` : `Expand ${project.name}`}
          style={{ marginLeft: "1.1rem" }}
        >
          <ChevronDown size={14} aria-hidden />
        </button>
        <Link href={href} className="sidebar-link" aria-current={pathname === href ? "page" : undefined} style={{ flex: 1 }}>
          <span className="sidebar-link__label">{project.name}</span>
        </Link>
      </div>
      {expanded && projectNav(project.id).map((item) => <SidebarLeaf key={item.href} item={item} pathname={pathname} depth={2} />)}
    </div>
  );
}

function WorkspaceSwitcherMenu({
  tenantName,
  tenants,
  currentTenantId,
  onSwitch,
  collapsed,
}: {
  tenantName: string | undefined;
  tenants: { tenant_id: string; tenant_name: string; role: string }[] | undefined;
  currentTenantId: string | undefined;
  onSwitch: (tenantId: string) => void;
  collapsed: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const label = tenantName ?? "Workspace";

  return (
    <DropdownMenu
      align="left"
      trigger={
        <button type="button" className="workspace-switcher">
          <span className="workspace-switcher__avatar">{initials(label)}</span>
          {!collapsed && (
            <span className="workspace-switcher__meta">
              <span className="workspace-switcher__name">{label}</span>
              <span className="workspace-switcher__role">Workspace</span>
            </span>
          )}
          {!collapsed && <ChevronsUpDown size={14} color="rgba(255,255,255,0.5)" aria-hidden />}
        </button>
      }
    >
      <p className="command-palette__group-label" style={{ padding: "var(--space-2) var(--space-3) 0" }}>
        Your workspaces
      </p>
      {(tenants ?? []).map((t) => (
        <MenuItem
          key={t.tenant_id}
          onClick={() => {
            if (t.tenant_id === currentTenantId || busy) return;
            setBusy(true);
            onSwitch(t.tenant_id);
          }}
        >
          {t.tenant_name}
          {t.tenant_id === currentTenantId && " · current"}
        </MenuItem>
      ))}
      <MenuSeparator />
      <MenuItem href="/app/settings/organization">Workspace settings</MenuItem>
    </DropdownMenu>
  );
}
