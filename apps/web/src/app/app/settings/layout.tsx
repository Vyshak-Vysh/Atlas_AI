"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { PageHeader } from "@/components/shell/PageHeader";

const SECTIONS = [
  { href: "/app/settings/profile", label: "Your profile" },
  { href: "/app/settings/organization", label: "Organization" },
  { href: "/app/settings/members", label: "Members" },
  { href: "/app/settings/roles", label: "Roles & permissions" },
  { href: "/app/settings/security", label: "Security" },
  { href: "/app/settings/billing", label: "Billing" },
];

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div>
      <PageHeader title="Settings" />
      <div style={{ display: "grid", gridTemplateColumns: "14rem minmax(0,1fr)", gap: "var(--space-6)" }} className="settings-layout">
        <nav className="sidebar-nav" style={{ padding: 0, background: "none" }}>
          {SECTIONS.map((s) => {
            const active = pathname === s.href;
            return (
              <Link
                key={s.href}
                href={s.href}
                style={{
                  display: "block",
                  padding: "var(--space-2) var(--space-3)",
                  borderRadius: "var(--radius-md)",
                  fontSize: "var(--font-size-sm)",
                  textDecoration: "none",
                  color: active ? "var(--color-brand-700)" : "var(--text-secondary)",
                  background: active ? "var(--color-brand-50)" : "transparent",
                  fontWeight: active ? "var(--font-weight-medium)" : "var(--font-weight-regular)",
                }}
              >
                {s.label}
              </Link>
            );
          })}
        </nav>
        <div>{children}</div>
      </div>
    </div>
  );
}
