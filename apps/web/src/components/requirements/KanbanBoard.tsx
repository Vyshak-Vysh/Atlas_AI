"use client";

import { DndContext, PointerSensor, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";

import { useUpdateRequirement } from "@/hooks/useRequirements";
import { TASK_STATUS_COLUMNS } from "@/lib/status";
import type { RequirementResponse } from "@/lib/types";
import { TaskColumn } from "./TaskColumn";

export function KanbanBoard({
  requirements,
  projectId,
  canDrag,
  onOpenTask,
}: {
  requirements: RequirementResponse[];
  projectId: string;
  canDrag: boolean;
  onOpenTask: (id: string) => void;
}) {
  const updateRequirement = useUpdateRequirement(projectId);
  // A small movement threshold so a plain click-to-open isn't swallowed as
  // a zero-distance drag (dnd-kit's PointerSensor otherwise activates
  // immediately on pointer down).
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over) return;
    const requirement = requirements.find((r) => r.id === active.id);
    const newStatus = String(over.id);
    if (!requirement || requirement.task_status === newStatus) return;
    updateRequirement.mutate({ requirementId: requirement.id, task_status: newStatus });
  }

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div className="kanban-board">
        {TASK_STATUS_COLUMNS.map((column) => (
          <TaskColumn
            key={column.value}
            status={column.value}
            label={column.label}
            requirements={requirements.filter((r) => r.task_status === column.value)}
            projectId={projectId}
            draggable={canDrag}
            onOpenTask={onOpenTask}
          />
        ))}
      </div>
    </DndContext>
  );
}
