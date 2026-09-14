"use client";

import { Drawer } from "@/components/ui/Drawer";
import { TaskDetailContent } from "./TaskDetailContent";

export function TaskDetailDrawer({
  requirementId,
  projectId,
  onClose,
}: {
  requirementId: string | null;
  projectId: string;
  onClose: () => void;
}) {
  return (
    <Drawer open={requirementId !== null} onClose={onClose} title="Task">
      {requirementId && (
        // Keyed by requirementId so switching tasks while the drawer stays
        // open fully remounts the content — otherwise local state (draft
        // text, active tab) would leak from the previous task into this one.
        <TaskDetailContent key={requirementId} requirementId={requirementId} projectId={projectId} onDeleted={onClose} />
      )}
    </Drawer>
  );
}
