"use client";

import { History } from "lucide-react";

import { useRequirementHistory } from "@/hooks/useRequirements";
import { formatRelativeTime, titleCase } from "@/lib/format";
import { EmptyState } from "@/components/ui/EmptyState";
import type { RequirementHistoryEntryResponse } from "@/lib/types";

function describe(entry: RequirementHistoryEntryResponse): string {
  const actor = entry.actor_display_name ?? "Someone";
  if (entry.event_type === "REQUIREMENT_CREATED") return `${actor} created this task`;
  if (entry.event_type === "REQUIREMENT_DELETED") return `${actor} deleted this task`;
  if (entry.event_type.startsWith("REQUIREMENT_COMMENT")) {
    const verb = entry.event_type.endsWith("ADDED") ? "added a comment" : entry.event_type.endsWith("DELETED") ? "deleted a comment" : "edited a comment";
    return `${actor} ${verb}`;
  }
  if (entry.field) {
    const from = entry.old_value === null || entry.old_value === undefined ? "—" : String(entry.old_value);
    const to = entry.new_value === null || entry.new_value === undefined ? "—" : String(entry.new_value);
    return `${actor} changed ${titleCase(entry.field)} from "${from.replaceAll("_", " ")}" to "${to.replaceAll("_", " ")}"`;
  }
  return `${actor} updated this task`;
}

export function TaskHistoryTimeline({ requirementId, projectId }: { requirementId: string; projectId: string }) {
  const { data: entries, isLoading } = useRequirementHistory(requirementId, projectId);

  if (isLoading) {
    return <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-tertiary)" }}>Loading history…</p>;
  }

  if (!entries || entries.length === 0) {
    return (
      <EmptyState icon={History} title="No changes recorded yet" description="Edits, status changes, and comments on this task will appear here with who made them and when." />
    );
  }

  return (
    <div className="timeline">
      {entries.map((entry) => (
        <div key={entry.id} className="timeline-item">
          <div className="timeline-item__rail" />
          <div>
            <p className="timeline-item__date">{formatRelativeTime(entry.created_at)}</p>
            <p className="timeline-item__title">{describe(entry)}</p>
            {entry.actor_email && (
              <p className="timeline-item__description">{entry.actor_email}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
