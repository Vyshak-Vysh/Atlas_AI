import { AlertTriangle, HelpCircle, ShieldAlert } from "lucide-react";

import { formatDateTime } from "@/lib/format";
import { findingStatusDisplay } from "@/lib/status";
import type { FindingResponse } from "@/lib/types";
import { StatusBadge } from "@/components/ui/Badge";
import { ConfidenceMeter } from "./ConfidenceMeter";

export function FindingPanel({ finding }: { finding: FindingResponse }) {
  const facts = finding.facts.filter((f): f is string => typeof f === "string");
  const inferences = finding.inferences.filter((f): f is string => typeof f === "string");

  return (
    <div className="finding-panel">
      <div className="finding-panel__header">
        <div>
          <StatusBadge status={findingStatusDisplay(finding.status)} />
          <h2 className="finding-panel__title" style={{ marginTop: "var(--space-3)" }}>
            {finding.summary}
          </h2>
        </div>
      </div>

      <div className="finding-panel__section" style={{ borderTop: "none", paddingTop: 0, marginTop: "var(--space-4)" }}>
        <ConfidenceMeter confidence={finding.confidence} />
      </div>

      {finding.requires_human_review && (
        <div className="uncertainty-callout" style={{ marginTop: "var(--space-4)" }}>
          <ShieldAlert size={16} aria-hidden style={{ flexShrink: 0 }} />
          <span>This finding requires human review before it should be treated as final.</span>
        </div>
      )}

      {facts.length > 0 && (
        <div className="finding-panel__section">
          <p className="finding-panel__section-title">Facts</p>
          <ul style={{ margin: 0, paddingLeft: "1.1rem", display: "grid", gap: "var(--space-2)", fontSize: "var(--font-size-sm)" }}>
            {facts.map((fact, i) => (
              <li key={i}>{fact}</li>
            ))}
          </ul>
        </div>
      )}

      {inferences.length > 0 && (
        <div className="finding-panel__section">
          <p className="finding-panel__section-title">Inferences</p>
          <ul style={{ margin: 0, paddingLeft: "1.1rem", display: "grid", gap: "var(--space-2)", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)" }}>
            {inferences.map((inference, i) => (
              <li key={i}>{inference}</li>
            ))}
          </ul>
        </div>
      )}

      {finding.conflicts.length > 0 && (
        <div className="finding-panel__section">
          <p className="finding-panel__section-title">
            <AlertTriangle size={14} aria-hidden style={{ color: "var(--color-warning-600)" }} /> Conflicting evidence
          </p>
          {finding.conflicts.map((conflict, i) => (
            <div key={i} className="conflict-callout" style={{ marginBottom: i < finding.conflicts.length - 1 ? "var(--space-3)" : 0, flexDirection: "column" }}>
              <div className="conflict-pair">
                <div className="conflict-pair__side">
                  <p style={{ margin: 0, fontWeight: "var(--font-weight-semibold)" }}>Side A</p>
                  <p style={{ margin: "var(--space-1) 0 0" }}>{conflict.side_a_summary ?? "—"}</p>
                </div>
                <div className="conflict-pair__side">
                  <p style={{ margin: 0, fontWeight: "var(--font-weight-semibold)" }}>Side B</p>
                  <p style={{ margin: "var(--space-1) 0 0" }}>{conflict.side_b_summary ?? "—"}</p>
                </div>
              </div>
              {conflict.why_it_matters && (
                <p style={{ margin: "var(--space-3) 0 0" }}>
                  <strong>Why it matters:</strong> {conflict.why_it_matters}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {finding.missing_evidence.length > 0 && (
        <div className="finding-panel__section">
          <p className="finding-panel__section-title">
            <HelpCircle size={14} aria-hidden /> Missing evidence
          </p>
          {finding.missing_evidence.map((missing, i) => (
            <div key={i} className="uncertainty-callout" style={{ marginBottom: i < finding.missing_evidence.length - 1 ? "var(--space-2)" : 0 }}>
              <div>
                {missing.what_was_searched && <p style={{ margin: 0 }}>Searched: {missing.what_was_searched}</p>}
                {missing.what_was_unavailable && <p style={{ margin: "var(--space-1) 0 0" }}>Unavailable: {missing.what_was_unavailable}</p>}
                {missing.what_would_resolve_it && (
                  <p style={{ margin: "var(--space-1) 0 0" }}>Would resolve it: {missing.what_would_resolve_it}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {finding.citations.length > 0 && (
        <div className="finding-panel__section">
          <p className="finding-panel__section-title">Supporting evidence ({finding.citations.length})</p>
          <div style={{ display: "grid", gap: "var(--space-2)" }}>
            {finding.citations.map((citation, i) => (
              <div key={i} className="card" style={{ padding: "var(--space-3) var(--space-4)" }}>
                <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "baseline" }}>
                  {citation.citation_label && (
                    <span style={{ fontFamily: "var(--font-family-mono)", fontWeight: "var(--font-weight-semibold)", color: "var(--text-tertiary)", fontSize: "var(--font-size-xs)" }}>
                      {citation.citation_label}
                    </span>
                  )}
                  {citation.location.page_number != null && (
                    <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
                      Page {citation.location.page_number}
                    </span>
                  )}
                </div>
                <p style={{ margin: "var(--space-2) 0 0", fontSize: "var(--font-size-sm)", fontStyle: "italic" }}>
                  &ldquo;{citation.quote}&rdquo;
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <p style={{ marginTop: "var(--space-5)", fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
        Finding created {formatDateTime(finding.created_at)}
      </p>
    </div>
  );
}
