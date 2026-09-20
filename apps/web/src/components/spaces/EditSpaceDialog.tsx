"use client";

import { useEffect, useState } from "react";

import { useUpdateSpace } from "@/hooks/useSpaces";
import { ApiError } from "@/lib/api";
import type { SpaceResponse } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/Field";
import { SPACE_SWATCH_COLORS } from "./CreateSpaceDialog";

/** Sibling of CreateSpaceDialog for editing an existing space in place —
 * name, description, color, and lifecycle status (ACTIVE/ON_HOLD/ARCHIVED). */
export function EditSpaceDialog({ open, onClose, space }: { open: boolean; onClose: () => void; space: SpaceResponse }) {
  const updateSpace = useUpdateSpace(space.id);
  const [name, setName] = useState(space.name);
  const [description, setDescription] = useState(space.description ?? "");
  const [color, setColor] = useState(space.color ?? SPACE_SWATCH_COLORS[0]);
  const [status, setStatus] = useState(space.status);
  const [error, setError] = useState<string | null>(null);

  // Re-sync local state whenever a different (or freshly-fetched) space is
  // opened for editing — the dialog instance is reused across opens.
  useEffect(() => {
    if (open) {
      setName(space.name);
      setDescription(space.description ?? "");
      setColor(space.color ?? SPACE_SWATCH_COLORS[0]);
      setStatus(space.status);
      setError(null);
    }
  }, [open, space]);

  async function handleSubmit() {
    setError(null);
    try {
      await updateSpace.mutateAsync({
        name: name.trim(),
        description: description.trim(),
        color,
        status,
      });
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail ?? err.message) : "Failed to update space.");
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Edit space"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={updateSpace.isPending} disabled={!name.trim()}>
            Save changes
          </Button>
        </>
      }
    >
      <div style={{ display: "grid", gap: "var(--space-4)" }}>
        {error && (
          <div className="error-state">
            <p style={{ margin: 0, fontSize: "var(--font-size-sm)" }}>{error}</p>
          </div>
        )}
        <Field label="Name" htmlFor="edit-space-name">
          <Input id="edit-space-name" value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Description" htmlFor="edit-space-description">
          <Textarea id="edit-space-description" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <Field label="Status" htmlFor="edit-space-status">
          <Select id="edit-space-status" value={status} onChange={(e) => setStatus(e.target.value)}>
            {["ACTIVE", "ON_HOLD", "ARCHIVED"].map((s) => (
              <option key={s} value={s}>
                {s.replaceAll("_", " ")}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Color">
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            {SPACE_SWATCH_COLORS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                aria-label={`Choose color ${c}`}
                style={{
                  width: "1.75rem",
                  height: "1.75rem",
                  borderRadius: "var(--radius-full)",
                  background: c,
                  border: color === c ? "2px solid var(--text-primary)" : "2px solid transparent",
                  cursor: "pointer",
                }}
              />
            ))}
          </div>
        </Field>
      </div>
    </Dialog>
  );
}
