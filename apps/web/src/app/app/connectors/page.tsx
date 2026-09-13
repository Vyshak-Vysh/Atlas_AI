"use client";

import { useQueries } from "@tanstack/react-query";
import { Plug } from "lucide-react";
import Link from "next/link";

import { useProjects } from "@/hooks/useProjects";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonLines } from "@/components/ui/Skeleton";

export default function GlobalConnectorsPage() {
  const { data: projects, isLoading } = useProjects();

  const results = useQueries({
    queries: (projects ?? []).map((project) => ({
      queryKey: ["connectors", project.id],
      queryFn: () => api.listConnectors(project.id),
      enabled: !!projects,
    })),
  });

  return (
    <div>
      <PageHeader title="Connectors" description="Evidence sources connected per project." />

      {isLoading ? (
        <SkeletonLines count={4} />
      ) : !projects || projects.length === 0 ? (
        <EmptyState icon={Plug} title="No projects yet" description="Connectors are managed per project — create a project first." />
      ) : (
        <div style={{ display: "grid", gap: "var(--space-3)", gridTemplateColumns: "repeat(auto-fill, minmax(16rem, 1fr))" }}>
          {projects.map((p, i) => {
            const connected = (results[i]?.data ?? []).filter((c) => c.connector?.status === "ACTIVE").length;
            return (
              <Link key={p.id} href={`/app/projects/${p.id}/connectors`} className="card card--interactive" style={{ padding: "var(--space-5)", textDecoration: "none", color: "inherit" }}>
                <Plug size={18} aria-hidden style={{ color: "var(--color-brand-700)" }} />
                <p style={{ margin: "var(--space-3) 0 0", fontWeight: "var(--font-weight-medium)" }}>{p.name}</p>
                <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
                  {results[i]?.isLoading ? "Loading…" : `${connected} connector${connected === 1 ? "" : "s"} active`}
                </p>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
