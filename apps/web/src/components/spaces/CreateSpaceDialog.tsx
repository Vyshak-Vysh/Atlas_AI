"use client";

import { useState } from "react";

import { useCreateSpace } from "@/hooks/useSpaces";
import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field, Input, Textarea } from "@/components/ui/Field";

export const SPACE_SWATCH_COLORS = ["#7C3AED", "#2563EB", "#059669", "#D97706", "#DC2626", "#DB2777"];

export function CreateSpaceDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated?: (spaceId: string) => void;
}) {
  const createSpace = useCreateSpace();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [color, setColor] = useState(SPACE_SWATCH_COLORS[0]);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setError(null);
    try {
      const space = await createSpace.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
        color,
      });
      setName("");
      setDescription("");
      onClose();
      onCreated?.(space.id);
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail ?? err.message) : "Failed to create space.");
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="New space"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={createSpace.isPending} disabled={!name.trim()}>
            Create space
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
        <Field label="Name" htmlFor="space-name">
          <Input id="space-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Engineering" />
        </Field>
        <Field label="Description" htmlFor="space-description">
          <Textarea id="space-description" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
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
