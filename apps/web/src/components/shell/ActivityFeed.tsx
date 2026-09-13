import { auditEventIcon, auditEventLabel } from "@/lib/audit";
import { formatRelativeTime } from "@/lib/format";
import type { AuditEventResponse } from "@/lib/types";
import { EmptyState } from "@/components/ui/EmptyState";
import { Activity } from "lucide-react";

export function ActivityFeed({ events, limit = 8 }: { events: AuditEventResponse[]; limit?: number }) {
  if (events.length === 0) {
    return <EmptyState icon={Activity} title="No activity yet" description="Actions across your workspace will appear here." />;
  }

  return (
    <div className="timeline">
      {events.slice(0, limit).map((event) => {
        const Icon = auditEventIcon(event.event_type);
        return (
          <div key={event.id} className="timeline-item">
            <div className="timeline-item__rail" />
            <div>
              <p className="timeline-item__date">{formatRelativeTime(event.created_at)}</p>
              <p className="timeline-item__title" style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <Icon size={14} aria-hidden style={{ color: "var(--text-tertiary)" }} />
                {auditEventLabel(event.event_type)}
              </p>
              {event.target_type && (
                <p className="timeline-item__description">
                  {event.target_type}
                  {event.target_id && ` · ${event.target_id.slice(0, 8)}`}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
