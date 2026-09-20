"use client";

import { Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useFindingsAcrossProjects } from "@/hooks/useWorkspaceSummary";
import { formatPercent, formatRelativeTime } from "@/lib/format";
import { findingStatusDisplay } from "@/lib/status";
import { PageHeader } from "@/components/shell/PageHeader";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination, usePagination } from "@/components/ui/Pagination";
import { SkeletonTable } from "@/components/ui/Skeleton";

export default function GlobalFindingsPage() {
  const router = useRouter();
  const { all, isLoading } = useFindingsAcrossProjects();
  const [projectFilter, setProjectFilter] = useState("ALL");
  const [page, setPage] = useState(1);

  const projects = Array.from(new Map(all.map((f) => [f.project.id, f.project])).values());
  const filtered = (projectFilter === "ALL" ? all : all.filter((f) => f.project.id === projectFilter))
    .slice()
    .sort((a, b) => new Date(b.finding.created_at).getTime() - new Date(a.finding.created_at).getTime());
  const { pageRows, page: currentPage, pageCount } = usePagination(filtered, page, setPage);

  return (
    <div>
      <PageHeader title="Findings" description="Every finding across every project you have access to." />

      {projects.length > 0 && (
        <div style={{ marginBottom: "var(--space-5)" }}>
          <select
            className="select"
            style={{ maxWidth: "16rem" }}
            value={projectFilter}
            onChange={(e) => {
              setProjectFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="ALL">All projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {isLoading ? (
        <SkeletonTable rows={6} />
      ) : filtered.length === 0 ? (
        <EmptyState icon={Sparkles} title="No findings yet" description="Findings appear once a project's investigations complete." />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Summary</th>
                <th>Project</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map(({ project, finding }) => (
                <tr key={finding.id} className="is-clickable" onClick={() => router.push(`/app/projects/${project.id}/findings/${finding.id}`)}>
                  <td style={{ maxWidth: "26rem" }}>{finding.summary}</td>
                  <td>{project.name}</td>
                  <td>
                    <StatusBadge status={findingStatusDisplay(finding.status)} />
                  </td>
                  <td>{formatPercent(finding.confidence)}</td>
                  <td>{formatRelativeTime(finding.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={currentPage} pageCount={pageCount} onPageChange={setPage} totalItems={filtered.length} pageSize={25} />
        </div>
      )}
    </div>
  );
}
