"use client";

import { usePathname, useParams } from "next/navigation";
import Link from "next/link";
import type { ReactNode } from "react";

import { useProjectOverview } from "@/hooks/useProjects";
import { projectStatusDisplay } from "@/lib/status";
import { projectNav } from "@/lib/nav";
import { StatusBadge } from "@/components/ui/Badge";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";

export default function ProjectLayout({ children }: { children: ReactNode }) {
  const params = useParams<{ projectId: string }>();
  const pathname = usePathname();
  const { data: overview, isLoading, error, refetch } = useProjectOverview(params.projectId);

  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} title="Couldn't load this project" />;
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
        {isLoading ? (
          <Skeleton style={{ height: "1.75rem", width: "16rem" }} />
        ) : (
          overview && (
            <>
              <h1 style={{ margin: 0, fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-semibold)" }}>
                {overview.project.name}
              </h1>
              <StatusBadge status={projectStatusDisplay(overview.project.status)} />
              {overview.project.client_name && (
                <span style={{ color: "var(--text-tertiary)", fontSize: "var(--font-size-sm)" }}>
                  {overview.project.client_name}
                </span>
              )}
            </>
          )
        )}
      </div>

      <nav className="tabs" aria-label="Project sections">
        {projectNav(params.projectId).map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link key={item.href} href={item.href} className="tab" aria-current={active ? "page" : undefined}>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {children}
    </div>
  );
}
