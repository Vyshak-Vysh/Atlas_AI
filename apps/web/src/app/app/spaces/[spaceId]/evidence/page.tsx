"use client";

import { useQueries } from "@tanstack/react-query";
import { FileSearch, Search } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { useSpaceProjects } from "@/hooks/useSpaces";
import { api } from "@/lib/api";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Field";
import { SkeletonLines } from "@/components/ui/Skeleton";

/**
 * Evidence search scoped to one client's projects — the same underlying
 * per-project search endpoint the workspace-wide Evidence search used
 * (fanned out across every project you can see, mixing every client
 * together), just narrowed to the projects that actually belong to this
 * Space. No new backend search infrastructure: this reuses the exact
 * `POST /api/v1/evidence/search` endpoint each project's own Evidence tab
 * already calls, once per project in the space.
 */
export default function SpaceEvidencePage() {
  const params = useParams<{ spaceId: string }>();
  const { data: projects, isLoading: projectsLoading } = useSpaceProjects(params.spaceId);
  const [query, setQuery] = useState("");
  const activeQuery = query.trim();

  const results = useQueries({
    queries: (projects ?? []).map((project) => ({
      queryKey: ["space-evidence-search", project.id, activeQuery],
      queryFn: () => api.searchEvidence(project.id, activeQuery, 5),
      enabled: activeQuery.length > 0,
    })),
  });

  const isSearching = activeQuery.length > 0;
  const isLoading = results.some((r) => r.isLoading);

  return (
    <div>
      <div className="search-field" style={{ marginBottom: "var(--space-5)" }}>
        <span className="search-field__icon">
          <Search size={16} aria-hidden />
        </span>
        <Input placeholder="Search evidence across this client's projects…" value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>

      {!isSearching ? (
        projectsLoading ? (
          <SkeletonLines count={4} />
        ) : !projects || projects.length === 0 ? (
          <EmptyState icon={FileSearch} title="No projects in this space yet" description="Add a project to this space, then its evidence can be searched from here." />
        ) : (
          <>
            <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-4)" }}>
              Or jump straight into a project's evidence:
            </p>
            <div style={{ display: "grid", gap: "var(--space-2)" }}>
              {projects.map((p) => (
                <Link
                  key={p.id}
                  href={`/app/projects/${p.id}/evidence`}
                  className="card card--interactive"
                  style={{ padding: "var(--space-4)", textDecoration: "none", color: "inherit" }}
                >
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
          {results.length > 0 && results.every((r) => (r.data?.results.length ?? 0) === 0) && (
            <EmptyState icon={FileSearch} title="No evidence found" description="No project in this space matched that search." />
          )}
        </div>
      )}
    </div>
  );
}
