"use client";

import { ChevronLeft, ChevronRight, ChevronsUpDown } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { useProjectOverview } from "@/hooks/useProjects";
import { useCurrentTenant, useMyTenants } from "@/hooks/useCurrentWorkspace";
import { useAuth } from "@/lib/auth-context";
import { initials } from "@/lib/format";
import { PRIMARY_NAV, SETTINGS_NAV, projectNav } from "@/lib/nav";
import { useUiStore } from "@/store/ui";
import { DropdownMenu, MenuItem, MenuSeparator } from "@/components/ui/DropdownMenu";

function useProjectIdFromPath(pathname: string): string | undefined {
  const match = pathname.match(/^\/app\/projects\/([0-9a-f-]{8,})/i);
  return match?.[1];
}

export function Sidebar() {
  const pathname = usePathname();
  const projectId = useProjectIdFromPath(pathname);
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const mobileOpen = useUiStore((s) => s.mobileNavOpen);
  const setMobileOpen = useUiStore((s) => s.setMobileNavOpen);
  const { switchTenant } = useAuth();

  const { data: overview } = useProjectOverview(projectId);
  const { data: tenant } = useCurrentTenant();
  const { data: tenants } = useMyTenants();

  const items = projectId ? projectNav(projectId) : PRIMARY_NAV;

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

      {projectId && (
        <div style={{ padding: "0 var(--space-5) var(--space-2)" }}>
          <Link
            href="/app/projects"
            style={{
              color: "rgba(255,255,255,0.55)",
              fontSize: "var(--font-size-xs)",
              textDecoration: "none",
            }}
          >
            ← All projects
          </Link>
          {!collapsed && overview && (
            <p
              style={{
                color: "#fff",
                fontWeight: "var(--font-weight-semibold)",
                fontSize: "var(--font-size-sm)",
                marginTop: "var(--space-1)",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
              title={overview.project.name}
            >
              {overview.project.name}
            </p>
          )}
        </div>
      )}

      <p className="sidebar-section-label">{projectId ? "Project" : "Workspace"}</p>
      <nav className="sidebar-nav">
        {items.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href} className="sidebar-link" aria-current={active ? "page" : undefined}>
              <Icon size={17} aria-hidden />
              <span className="sidebar-link__label">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <nav className="sidebar-nav" style={{ padding: 0, marginBottom: "var(--space-2)" }}>
          <Link
            href={SETTINGS_NAV.href}
            className="sidebar-link"
            aria-current={pathname.startsWith(SETTINGS_NAV.href) ? "page" : undefined}
          >
            <SETTINGS_NAV.icon size={17} aria-hidden />
            <span className="sidebar-link__label">{SETTINGS_NAV.label}</span>
          </Link>
        </nav>
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
      </div>
    </aside>
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
