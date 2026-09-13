"use client";

import { usePathname } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useUiStore } from "@/store/ui";
import { CommandPalette } from "./CommandPalette";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppShell({ children }: { children: ReactNode }) {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const mobileNavOpen = useUiStore((s) => s.mobileNavOpen);
  const setMobileNavOpen = useUiStore((s) => s.setMobileNavOpen);
  const pathname = usePathname();

  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname, setMobileNavOpen]);

  return (
    <div className="app-shell" data-sidebar-collapsed={collapsed}>
      <div className="mobile-nav-backdrop" data-open={mobileNavOpen} onClick={() => setMobileNavOpen(false)} />
      <Sidebar />
      <div className="app-main">
        <Topbar />
        <main className="app-content" id="main-content">
          {children}
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
