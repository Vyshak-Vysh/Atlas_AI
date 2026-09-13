"use client";

import { AlertTriangle, FileText, Search, Trash2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { useEvidenceSearch } from "@/hooks/useEvidenceSearch";
import { useDeleteSource, useSources } from "@/hooks/useSources";
import { formatDateTime, formatRelativeTime } from "@/lib/format";
import type { EvidenceCandidate, SourceRecordResponse } from "@/lib/types";
import { UploadPanel } from "@/components/evidence/UploadPanel";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Field";
import { SkeletonLines } from "@/components/ui/Skeleton";

type Selected = { kind: "source"; item: SourceRecordResponse } | { kind: "evidence"; item: EvidenceCandidate } | null;

export default function EvidenceExplorerPage() {
  const params = useParams<{ projectId: string }>();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Selected>(null);
  const [pendingDelete, setPendingDelete] = useState<SourceRecordResponse | null>(null);

  const sourcesQuery = useSources(params.projectId);
  const searchQuery = useEvidenceSearch(params.projectId, query);
  const deleteSource = useDeleteSource(params.projectId);

  const isSearching = query.trim().length > 0;
  const sourceById = new Map((sourcesQuery.data ?? []).map((s) => [s.id, s]));

  return (
    <div>
      <div style={{ marginBottom: "var(--space-5)" }}>
        <UploadPanel projectId={params.projectId} />
      </div>

      <div className="search-field" style={{ marginBottom: "var(--space-5)" }}>
        <span className="search-field__icon">
          <Search size={16} aria-hidden />
        </span>
        <Input
          placeholder="Search this project's evidence — e.g. “Is single sign-on in scope for phase 1?”"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="evidence-layout">
        <div className="evidence-list">
          {isSearching ? (
            searchQuery.isLoading ? (
              <SkeletonLines count={4} />
            ) : searchQuery.error ? (
              <ErrorState error={searchQuery.error} />
            ) : searchQuery.data && searchQuery.data.results.length > 0 ? (
              searchQuery.data.results.map((candidate) => (
                <button
                  key={candidate.evidence_chunk_id}
                  type="button"
                  className="evidence-item"
                  aria-selected={selected?.kind === "evidence" && selected.item.evidence_chunk_id === candidate.evidence_chunk_id}
                  onClick={() => setSelected({ kind: "evidence", item: candidate })}
                  style={{ textAlign: "left", width: "100%" }}
                >
                  <div className="evidence-item__meta">
                    <span className="evidence-type-icon">
                      <FileText size={13} aria-hidden />
                    </span>
                    <span>{sourceById.get(candidate.source_record_id)?.title ?? "Evidence"}</span>
                    {candidate.location.page_number !== null && <span>Page {candidate.location.page_number}</span>}
                  </div>
                  <p className="evidence-item__excerpt" style={{ marginTop: "var(--space-2)" }}>
                    {candidate.content.slice(0, 260)}
                    {candidate.content.length > 260 ? "…" : ""}
                  </p>
                </button>
              ))
            ) : (
              <EmptyState
                icon={Search}
                title="No evidence found"
                description="AtlasAI searched this project's connected sources and found no matching passages. This means no evidence exists for that query yet — not that the answer is out of scope."
              />
            )
          ) : sourcesQuery.isLoading ? (
            <SkeletonLines count={4} />
          ) : sourcesQuery.error ? (
            <ErrorState error={sourcesQuery.error} onRetry={() => sourcesQuery.refetch()} />
          ) : sourcesQuery.data && sourcesQuery.data.length > 0 ? (
            sourcesQuery.data.map((source) => (
              <div
                key={source.id}
                className="evidence-item"
                aria-selected={selected?.kind === "source" && selected.item.id === source.id}
                onClick={() => setSelected({ kind: "source", item: source })}
              >
                <div className="evidence-item__meta">
                  <span className="evidence-type-icon">
                    <FileText size={13} aria-hidden />
                  </span>
                  <span>{source.record_type}</span>
                  <span>·</span>
                  <span>{source.visibility}</span>
                  {source.ingestion_status === "PROCESSING" && (
                    <span className="badge badge--warning">Processing</span>
                  )}
                </div>
                <p className="evidence-item__title">{source.title ?? "Untitled source"}</p>
                <p className="evidence-item__excerpt">Added {formatRelativeTime(source.created_at)}</p>
              </div>
            ))
          ) : (
            <EmptyState
              icon={FileText}
              title="No evidence connected yet"
              description="Upload a document above, or connect a source, to start building this project's evidence base."
            />
          )}
        </div>

        <EvidencePreviewPanel
          selected={selected}
          source={selected?.kind === "evidence" ? sourceById.get(selected.item.source_record_id) : undefined}
          onDelete={selected?.kind === "source" ? () => setPendingDelete(selected.item) : undefined}
        />
      </div>

      <ConfirmDialog
        open={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        title="Delete this source?"
        description={
          <>
            Deleting &ldquo;{pendingDelete?.title}&rdquo; removes it and every evidence chunk derived from it from
            search and citations. This cannot be undone.
          </>
        }
        confirmLabel="Delete source"
        onConfirm={async () => {
          if (pendingDelete) {
            await deleteSource.mutateAsync(pendingDelete.id);
            setSelected(null);
          }
        }}
      />
    </div>
  );
}

function EvidencePreviewPanel({
  selected,
  source,
  onDelete,
}: {
  selected: Selected;
  source?: SourceRecordResponse;
  onDelete?: () => void;
}) {
  if (!selected) {
    return (
      <div className="card" style={{ padding: "var(--space-6)", textAlign: "center", color: "var(--text-tertiary)", fontSize: "var(--font-size-sm)" }}>
        Select a source or a search result to preview it here.
      </div>
    );
  }

  if (selected.kind === "source") {
    const s = selected.item;
    return (
      <div className="card" style={{ padding: "var(--space-5)" }}>
        <p style={{ margin: 0, fontWeight: "var(--font-weight-semibold)" }}>{s.title ?? "Untitled source"}</p>
        <dl style={{ marginTop: "var(--space-4)", display: "grid", gap: "var(--space-3)", fontSize: "var(--font-size-sm)" }}>
          <Row label="Type" value={s.record_type} />
          <Row label="Visibility" value={s.visibility} />
          <Row label="Status" value={s.ingestion_status} />
          <Row label="Added" value={formatDateTime(s.created_at)} />
        </dl>
        {onDelete && (
          <button type="button" className="button button--danger button--small" style={{ marginTop: "var(--space-4)" }} onClick={onDelete}>
            <Trash2 size={14} aria-hidden /> Delete source
          </button>
        )}
      </div>
    );
  }

  const e = selected.item;
  return (
    <div className="card" style={{ padding: "var(--space-5)" }}>
      <div className="evidence-item__meta" style={{ marginBottom: "var(--space-3)" }}>
        <span className="evidence-type-icon">
          <FileText size={13} aria-hidden />
        </span>
        <span>{source?.title ?? "Evidence source"}</span>
      </div>
      <blockquote style={{ margin: 0, fontSize: "var(--font-size-md)", lineHeight: "var(--line-height-relaxed)", borderLeft: "3px solid var(--border-default)", paddingLeft: "var(--space-3)" }}>
        {e.content}
      </blockquote>
      <dl style={{ marginTop: "var(--space-4)", display: "grid", gap: "var(--space-2)", fontSize: "var(--font-size-sm)" }}>
        {e.location.page_number !== null && <Row label="Page" value={String(e.location.page_number)} />}
        {e.location.speaker && <Row label="Speaker" value={e.location.speaker} />}
        {e.rerank_score !== null && <Row label="Relevance" value={e.rerank_score.toFixed(2)} />}
        {e.visibility === "INTERNAL" && (
          <div className="conflict-callout" style={{ marginTop: "var(--space-2)" }}>
            <AlertTriangle size={14} aria-hidden />
            <span>Internal-only evidence — hidden from client-facing views.</span>
          </div>
        )}
      </dl>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: "var(--space-3)" }}>
      <dt style={{ color: "var(--text-tertiary)" }}>{label}</dt>
      <dd style={{ margin: 0, fontWeight: "var(--font-weight-medium)", textAlign: "right" }}>{value}</dd>
    </div>
  );
}
