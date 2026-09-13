"use client";

import { FolderKanban, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useProjects } from "@/hooks/useProjects";
import { formatDate } from "@/lib/format";
import { projectStatusDisplay } from "@/lib/status";
import { PageHeader } from "@/components/shell/PageHeader";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Field";
import { SkeletonTable } from "@/components/ui/Skeleton";

const STATUS_FILTERS = ["ALL", "ACTIVE", "ON_HOLD", "COMPLETED", "ARCHIVED"] as const;

export default function ProjectsListPage() {
  const { data: projects, isLoading, error, refetch } = useProjects();
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query, 200);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]>("ALL");

  const filtered = useMemo(() => {
    return (projects ?? [])
      .filter((p) => statusFilter === "ALL" || p.status === statusFilter)
      .filter((p) => {
        const q = debouncedQuery.trim().toLowerCase();
        if (!q) return true;
        return p.name.toLowerCase().includes(q) || (p.client_name ?? "").toLowerCase().includes(q);
      });
  }, [projects, statusFilter, debouncedQuery]);

  return (
    <div>
      <PageHeader
        title="Projects"
        description="Every project you have access to in this workspace."
        actions={
          <Link href="/app/projects/new">
            <Button>
              <Plus size={16} aria-hidden /> New project
            </Button>
          </Link>
        }
      />

      <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-5)", flexWrap: "wrap" }}>
        <div className="search-field" style={{ minWidth: "16rem", flex: 1 }}>
          <span className="search-field__icon">
            <Search size={16} aria-hidden />
          </span>
          <Input placeholder="Search by project or client name…" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <select
          className="select"
          style={{ maxWidth: "12rem" }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as (typeof STATUS_FILTERS)[number])}
        >
          {STATUS_FILTERS.map((s) => (
            <option key={s} value={s}>
              {s === "ALL" ? "All statuses" : s.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <SkeletonTable rows={6} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title={projects && projects.length > 0 ? "No projects match your filters" : "No projects yet"}
          description={
            projects && projects.length > 0
              ? "Try a different search term or status filter."
              : "Create a project to start connecting evidence and asking scope questions."
          }
          actions={
            !(projects && projects.length > 0) && (
              <Link href="/app/projects/new">
                <Button size="small">Create project</Button>
              </Link>
            )
          }
        />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Project</th>
                <th>Client</th>
                <th>Status</th>
                <th>Timezone</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((project) => (
                <tr key={project.id}>
                  <td>
                    <Link href={`/app/projects/${project.id}/overview`} style={{ fontWeight: "var(--font-weight-medium)", color: "var(--text-primary)" }}>
                      {project.name}
                    </Link>
                    {project.code && <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>{project.code}</div>}
                  </td>
                  <td>{project.client_name ?? "—"}</td>
                  <td>
                    <StatusBadge status={projectStatusDisplay(project.status)} />
                  </td>
                  <td>{project.timezone}</td>
                  <td>{formatDate(project.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
