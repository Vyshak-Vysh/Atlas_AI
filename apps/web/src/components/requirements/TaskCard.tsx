"use client";

import { useDraggable } from "@dnd-kit/core";

import { useProjectMembers } from "@/hooks/useTeam";
import { useSprints } from "@/hooks/useSprints";
import { taskPriorityDisplay } from "@/lib/status";
import type { RequirementResponse } from "@/lib/types";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";

export function TaskCard({
  requirement,
  projectId,
  draggable,
  onOpen,
}: {
  requirement: RequirementResponse;
  projectId: string;
  draggable: boolean;
  onOpen: () => void;
}) {
  const { data: members } = useProjectMembers(projectId);
  const { data: sprints } = useSprints(projectId);
  const assignee = members?.find((m) => m.user_id === requirement.assignee_id);
  const sprint = sprints?.find((s) => s.id === requirement.sprint_id);
  const priority = taskPriorityDisplay(requirement.priority);

  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: requirement.id,
    disabled: !draggable,
  });

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn("kanban-card", isDragging && "kanban-card--dragging")}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter") onOpen();
      }}
      {...(draggable ? { ...attributes, ...listeners } : { role: "button", tabIndex: 0 })}
    >
      <p className="kanban-card__key">{requirement.key}</p>
      <p className="kanban-card__title">{requirement.title}</p>
      {sprint && (
        <div style={{ marginBottom: "var(--space-2)" }}>
          <Badge variant="discovery">{sprint.name}</Badge>
        </div>
      )}
      <div className="kanban-card__footer">
        <Badge variant={priority.variant}>{priority.label}</Badge>
        {assignee ? <Avatar name={assignee.display_name} size={22} /> : null}
      </div>
    </div>
  );
}
