"use client";

import { useDroppable } from "@dnd-kit/core";

import { cn } from "@/lib/cn";
import type { RequirementResponse } from "@/lib/types";
import { TaskCard } from "./TaskCard";

export function TaskColumn({
  status,
  label,
  requirements,
  projectId,
  draggable,
  onOpenTask,
}: {
  status: string;
  label: string;
  requirements: RequirementResponse[];
  projectId: string;
  draggable: boolean;
  onOpenTask: (id: string) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status });

  return (
    <div ref={setNodeRef} className={cn("kanban-column", isOver && "kanban-column--drag-over")}>
      <div className="kanban-column__header">
        <p className="kanban-column__title">{label}</p>
        <span className="kanban-column__count">{requirements.length}</span>
      </div>
      <div className="kanban-column__body">
        {requirements.map((requirement) => (
          <TaskCard
            key={requirement.id}
            requirement={requirement}
            projectId={projectId}
            draggable={draggable}
            onOpen={() => onOpenTask(requirement.id)}
          />
        ))}
      </div>
    </div>
  );
}
