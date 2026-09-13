"use client";

import type { ReactNode } from "react";

import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/shell/AppShell";

export default function AppSectionLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <AppShell>{children}</AppShell>
    </RequireAuth>
  );
}
