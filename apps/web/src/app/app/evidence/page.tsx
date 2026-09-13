"use client";

import { useQueries } from "@tanstack/react-query";
import { FileSearch, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { useProjects } from "@/hooks/useProjects";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Field";
import { SkeletonLines } from "@/components/ui/Skeleton";

export default function GlobalEvidencePage() {
  const { data: projects, isLoading: projectsLoading } = useProjects();
  const [query, setQuery] = useState("");
  const activeQuery = query.trim();

  const results = useQueries({
    queries: (projects ?? []).map((project) => ({
      queryKey: ["evidence-search", project.id, activeQuery],
      queryFn: () => api.searchEvidence(project.id, activeQuery, 5),
      enabled: activeQuery.length > 0,
    })),
  });

  const isSearching = activeQuery.length > 0;
  const isLoading = results.some((r) => r.isLoading);

  return (
    <div>
      <PageHeader
        title="Evidence"
        description="Search across every project's connected evidence. Each project also has its own dedicated Evidence Explorer with upload and browse."
      />

      <div className="search-field" style={{ marginBottom: "var(--space-5)" }}>
        <span className="search-field__icon">
          <Search size={16} aria-hidden />
        </span>
        <Input placeholder="Search across all your projects…" value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>

      {!isSearching ? (
        projectsLoading ? (
          <SkeletonLines count={4} />
        ) : (
          <>
            <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-4)" }}>
              Or jump straight into a project's evidence:
            </p>
            <div style={{ display: "grid", gap: "var(--space-2)" }}>
              {(projects ?? []).map((p) => (
                <Link key={p.id} href={`/app/projects/${p.id}/evidence`} className="card card--interactive" style={{ padding: "var(--space-4)", textDecoration: "none", color: "inherit" }}>
                  {p.name}
                </Link>
              ))}
            </div>
          </>
        )
      ) : isLoading ? (
        <SkeletonLines count={4} />
      ) : (
        <div style={{ display: "grid", gap: "var(--space-4)" }}>
          {(projects ?? []).map((project, i) => {
            const data = results[i]?.data;
            if (!data || data.results.length === 0) return null;
            return (
              <div key={project.id}>
                <p style={{ fontSize: "var(--font-size-sm)", fontWeight: "var(--font-weight-semibold)", marginBottom: "var(--space-2)" }}>
                  <Link href={`/app/projects/${project.id}/evidence`}>{project.name}</Link>
                </p>
                <div className="evidence-list">
                  {data.results.map((r) => (
                    <div key={r.evidence_chunk_id} className="evidence-item" style={{ cursor: "default" }}>
                      <p className="evidence-item__excerpt" style={{ marginTop: 0 }}>
                        {r.content.slice(0, 220)}
                        {r.content.length > 220 ? "…" : ""}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
          {results.every((r) => (r.data?.results.length ?? 0) === 0) && (
            <EmptyState icon={FileSearch} title="No evidence found" description="No project's evidence matched that search." />
          )}
        </div>
      )}
    </div>
  );
}
