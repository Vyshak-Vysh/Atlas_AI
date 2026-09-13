"use client";

import { Activity } from "lucide-react";
import { useMemo, useState } from "react";

import { useAuditEvents } from "@/hooks/useAuditEvents";
import { auditEventIcon, auditEventLabel } from "@/lib/audit";
import { formatDateTime } from "@/lib/format";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Field";
import { SkeletonTable } from "@/components/ui/Skeleton";

export default function AuditLogPage() {
  const { data: events, isLoading, error, refetch } = useAuditEvents(500);
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    if (!events) return [];
    const q = query.trim().toLowerCase();
    if (!q) return events;
    return events.filter((e) => auditEventLabel(e.event_type).toLowerCase().includes(q) || e.event_type.toLowerCase().includes(q) || (e.target_type ?? "").toLowerCase().includes(q));
  }, [events, query]);

  return (
    <div>
      <PageHeader title="Audit log" description="A read-only record of sensitive actions across this workspace." />

      <div style={{ marginBottom: "var(--space-5)", maxWidth: "24rem" }}>
        <Input placeholder="Filter by event type or target…" value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>

      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <SkeletonTable rows={8} />
      ) : filtered.length === 0 ? (
        <EmptyState icon={Activity} title="No matching audit events" />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Event</th>
                <th>Target</th>
                <th>Actor</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((event) => {
                const Icon = auditEventIcon(event.event_type);
                return (
                  <tr key={event.id}>
                    <td style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                      <Icon size={14} aria-hidden style={{ color: "var(--text-tertiary)" }} />
                      {auditEventLabel(event.event_type)}
                    </td>
                    <td>
                      {event.target_type ?? "—"}
                      {event.target_id && (
                        <span style={{ fontFamily: "var(--font-family-mono)", fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)", marginLeft: "var(--space-1)" }}>
                          {event.target_id.slice(0, 8)}
                        </span>
                      )}
                    </td>
                    <td>{event.actor_id ? event.actor_id.slice(0, 8) : "System"}</td>
                    <td>{formatDateTime(event.created_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
