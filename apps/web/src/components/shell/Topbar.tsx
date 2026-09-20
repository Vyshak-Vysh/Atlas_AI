"use client";

import { Bell, LogOut, Menu, Moon, Search, Settings, Sun, SunMoon, User } from "lucide-react";

import { usePendingApprovalNotifications } from "@/hooks/useNotifications";
import { useAuth } from "@/lib/auth-context";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { formatRelativeTime } from "@/lib/format";
import { useUiStore, type ThemePreference } from "@/store/ui";
import { Avatar } from "@/components/ui/Avatar";
import { DropdownMenu, MenuItem, MenuSeparator } from "@/components/ui/DropdownMenu";
import { Tooltip } from "@/components/ui/Tooltip";
import { BackButton } from "./BackButton";
import { Breadcrumbs } from "./Breadcrumbs";

const THEME_ICON: Record<ThemePreference, typeof Sun> = { light: Sun, dark: Moon, system: SunMoon };

export function Topbar() {
  const { logout } = useAuth();
  const { data: user } = useCurrentUser();
  const setCommandPaletteOpen = useUiStore((s) => s.setCommandPaletteOpen);
  const setMobileNavOpen = useUiStore((s) => s.setMobileNavOpen);
  const theme = useUiStore((s) => s.theme);
  const setTheme = useUiStore((s) => s.setTheme);
  const { items: notifications } = usePendingApprovalNotifications();

  const ThemeIcon = THEME_ICON[theme];

  return (
    <header className="app-topbar">
      <Tooltip label="Open navigation">
        <button
          type="button"
          className="topbar-icon-btn mobile-nav-trigger"
          onClick={() => setMobileNavOpen(true)}
          aria-label="Open navigation"
        >
          <Menu size={18} aria-hidden />
        </button>
      </Tooltip>

      <BackButton />
      <Breadcrumbs />

      <button
        type="button"
        className="search-field__icon"
        style={{ position: "static", marginLeft: "auto" }}
        onClick={() => setCommandPaletteOpen(true)}
        aria-label="Open search"
      >
        <span
          className="button button--secondary button--small"
          style={{ display: "inline-flex", gap: "var(--space-2)" }}
        >
          <Search size={14} aria-hidden /> Search
          <kbd style={{ fontSize: "var(--font-size-2xs)", opacity: 0.6 }}>⌘K</kbd>
        </span>
      </button>

      <DropdownMenu
        trigger={
          <Tooltip label="Notifications">
            <button type="button" className="topbar-icon-btn" aria-label="Notifications">
              <Bell size={18} aria-hidden />
              {notifications.length > 0 && <span className="topbar-icon-btn__dot" />}
            </button>
          </Tooltip>
        }
      >
        <p className="command-palette__group-label">Pending approvals</p>
        {notifications.length === 0 ? (
          <p style={{ padding: "var(--space-3)", fontSize: "var(--font-size-sm)", color: "var(--text-tertiary)" }}>
            Nothing waiting on you right now.
          </p>
        ) : (
          notifications.slice(0, 8).map((n) => (
            <MenuItem
              key={n.action.id}
              href={`/app/projects/${n.project.id}/approvals/${n.action.id}`}
            >
              <span style={{ display: "grid" }}>
                <span>{n.action.action_type.replaceAll("_", " ")}</span>
                <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
                  {n.project.name} · {formatRelativeTime(n.action.created_at)}
                </span>
              </span>
            </MenuItem>
          ))
        )}
        <MenuSeparator />
        <MenuItem href="/app/approvals">View all approvals</MenuItem>
      </DropdownMenu>

      <DropdownMenu
        trigger={
          <Tooltip label="Change theme">
            <button type="button" className="topbar-icon-btn" aria-label="Change theme">
              <ThemeIcon size={18} aria-hidden />
            </button>
          </Tooltip>
        }
      >
        <MenuItem icon={<Sun size={15} aria-hidden />} onClick={() => setTheme("light")}>
          Light
        </MenuItem>
        <MenuItem icon={<Moon size={15} aria-hidden />} onClick={() => setTheme("dark")}>
          Dark
        </MenuItem>
        <MenuItem icon={<SunMoon size={15} aria-hidden />} onClick={() => setTheme("system")}>
          System
        </MenuItem>
      </DropdownMenu>

      <DropdownMenu
        trigger={
          <button type="button" className="user-menu-trigger" aria-label="User menu">
            <Avatar name={user?.display_name ?? "?"} />
          </button>
        }
      >
        <div style={{ padding: "var(--space-2) var(--space-3)" }}>
          <p style={{ fontWeight: "var(--font-weight-semibold)", fontSize: "var(--font-size-sm)" }}>
            {user?.display_name ?? "…"}
          </p>
          <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>{user?.email}</p>
        </div>
        <MenuSeparator />
        <MenuItem icon={<User size={15} aria-hidden />} href="/app/settings/profile">
          Your profile
        </MenuItem>
        <MenuItem icon={<Settings size={15} aria-hidden />} href="/app/settings">
          Settings
        </MenuItem>
        <MenuSeparator />
        <MenuItem
          icon={<LogOut size={15} aria-hidden />}
          danger
          onClick={() => {
            void logout();
          }}
        >
          Sign out
        </MenuItem>
      </DropdownMenu>
    </header>
  );
}
