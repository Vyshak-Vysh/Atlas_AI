"use client";

import { FileText } from "lucide-react";
import Link from "next/link";

import { useProjects } from "@/hooks/useProjects";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonLines } from "@/components/ui/Skeleton";

export default function GlobalReportsPage() {
  const { data: projects, isLoading } = useProjects();

  return (
    <div>
      <PageHeader title="Reports" description="Generate an evidence-backed report for any project — computed live from that project's current data." />

      {isLoading ? (
        <SkeletonLines count={4} />
      ) : !projects || projects.length === 0 ? (
        <EmptyState icon={FileText} title="No projects yet" description="Create a project first — reports are generated per project." />
      ) : (
        <div style={{ display: "grid", gap: "var(--space-3)", gridTemplateColumns: "repeat(auto-fill, minmax(16rem, 1fr))" }}>
          {projects.map((p) => (
            <Link key={p.id} href={`/app/projects/${p.id}/reports`} className="card card--interactive" style={{ padding: "var(--space-5)", textDecoration: "none", color: "inherit" }}>
              <FileText size={18} aria-hidden style={{ color: "var(--color-brand-700)" }} />
              <p style={{ margin: "var(--space-3) 0 0", fontWeight: "var(--font-weight-medium)" }}>{p.name}</p>
              {p.client_name && <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>{p.client_name}</p>}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
