"use client";

import { CalendarRange, Plus } from "lucide-react";
import { useState } from "react";

import { useCreateSprint, useSprints, useUpdateSprint } from "@/hooks/useSprints";
import { ApiError } from "@/lib/api";
import { sprintStatusDisplay } from "@/lib/status";
import { useToast } from "@/lib/toast";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Field, Input, Select } from "@/components/ui/Field";

const SPRINT_STATUSES = ["PLANNED", "ACTIVE", "COMPLETED", "CANCELLED"];

/**
 * The one place sprints get created and have their status moved along —
 * previously there was no UI for this at all, so the "Sprint" picker
 * everywhere else in Tasks always showed "No sprint" for every real
 * project. Opened from the Tasks toolbar; edits here are reflected
 * immediately in the sprint filter and the Add-task/task-detail pickers
 * via the shared `["sprints", projectId]` query key.
 */
export function ManageSprintsDialog({ open, onClose, projectId }: { open: boolean; onClose: () => void; projectId: string }) {
  const { data: sprints, isLoading } = useSprints(projectId);
  const updateSprint = useUpdateSprint(projectId);
  const { toast } = useToast();
  const [showCreate, setShowCreate] = useState(false);

  return (
    <Dialog open={open} onClose={onClose} title="Manage sprints" footer={<Button onClick={onClose}>Done</Button>}>
      <div style={{ display: "grid", gap: "var(--space-4)" }}>
        {isLoading ? null : !sprints || sprints.length === 0 ? (
          showCreate ? null : (
            <EmptyState
              icon={CalendarRange}
              title="No sprints yet"
              description="Create a sprint to start planning tasks into time-boxed cycles."
              actions={
                <Button size="small" onClick={() => setShowCreate(true)}>
                  <Plus size={14} aria-hidden /> New sprint
                </Button>
              }
            />
          )
        ) : (
          <div style={{ display: "grid", gap: "var(--space-2)" }}>
            {sprints
              .slice()
              .sort((a, b) => a.sprint_number - b.sprint_number)
              .map((sprint) => (
                <div
                  key={sprint.id}
                  className="card"
                  style={{ padding: "var(--space-3)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-3)" }}
                >
                  <div style={{ minWidth: 0 }}>
                    <p style={{ margin: 0, fontSize: "var(--font-size-sm)", fontWeight: "var(--font-weight-medium)" }}>
                      Sprint {sprint.sprint_number}: {sprint.name}
                    </p>
                    {(sprint.start_date || sprint.end_date) && (
                      <p style={{ margin: "0.15rem 0 0", fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
                        {sprint.start_date ?? "—"} – {sprint.end_date ?? "—"}
                      </p>
                    )}
                  </div>
                  <Select
                    value={sprint.status}
                    onChange={async (e) => {
                      try {
                        await updateSprint.mutateAsync({ sprintId: sprint.id, status: e.target.value });
                      } catch (err) {
                        toast({
                          title: "Couldn't update sprint",
                          description: err instanceof ApiError ? String(err.detail) : undefined,
                          variant: "danger",
                        });
                      }
                    }}
                    style={{ maxWidth: "9rem" }}
                    aria-label={`Status for ${sprint.name}`}
                  >
                    {SPRINT_STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {sprintStatusDisplay(s).label}
                      </option>
                    ))}
                  </Select>
                </div>
              ))}
          </div>
        )}

        {!showCreate && sprints && sprints.length > 0 && (
          <Button variant="secondary" size="small" onClick={() => setShowCreate(true)} style={{ justifySelf: "start" }}>
            <Plus size={14} aria-hidden /> New sprint
          </Button>
        )}

        {showCreate && (
          <CreateSprintForm
            projectId={projectId}
            nextNumber={(sprints ?? []).reduce((max, s) => Math.max(max, s.sprint_number), 0) + 1}
            onDone={() => setShowCreate(false)}
          />
        )}
      </div>
    </Dialog>
  );
}

function CreateSprintForm({ projectId, nextNumber, onDone }: { projectId: string; nextNumber: number; onDone: () => void }) {
  const createSprint = useCreateSprint(projectId);
  const [name, setName] = useState(`Sprint ${nextNumber}`);
  const [sprintNumber, setSprintNumber] = useState(nextNumber);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setError(null);
    try {
      await createSprint.mutateAsync({
        name: name.trim(),
        sprint_number: sprintNumber,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail ?? err.message) : "Failed to create sprint.");
    }
  }

  return (
    <div className="card" style={{ padding: "var(--space-4)", display: "grid", gap: "var(--space-3)" }}>
      {error && (
        <div className="error-state">
          <p style={{ margin: 0, fontSize: "var(--font-size-sm)" }}>{error}</p>
        </div>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 5rem", gap: "var(--space-3)" }}>
        <Field label="Name" htmlFor="sprint-name">
          <Input id="sprint-name" value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Number" htmlFor="sprint-number">
          <Input
            id="sprint-number"
            type="number"
            min={1}
            value={sprintNumber}
            onChange={(e) => setSprintNumber(Number(e.target.value))}
          />
        </Field>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)" }}>
        <Field label="Start date" htmlFor="sprint-start">
          <Input id="sprint-start" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </Field>
        <Field label="End date" htmlFor="sprint-end">
          <Input id="sprint-end" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </Field>
      </div>
      <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
        <Button variant="secondary" size="small" onClick={onDone}>
          Cancel
        </Button>
        <Button size="small" onClick={handleSubmit} loading={createSprint.isPending} disabled={!name.trim()}>
          Create sprint
        </Button>
      </div>
    </div>
  );
}
