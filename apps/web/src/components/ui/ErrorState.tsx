import { AlertOctagon, RefreshCw } from "lucide-react";

import { ApiError } from "@/lib/api";
import { Button } from "./Button";

export function ErrorState({ error, onRetry, title }: { error: unknown; onRetry?: () => void; title?: string }) {
  const message =
    error instanceof ApiError
      ? typeof error.detail === "string"
        ? error.detail
        : error.message
      : error instanceof Error
        ? error.message
        : "Something went wrong.";

  const correlationId = error instanceof ApiError ? error.status : undefined;

  return (
    <div className="error-state">
      <AlertOctagon size={20} aria-hidden style={{ flexShrink: 0, marginTop: "0.1rem" }} />
      <div style={{ flex: 1 }}>
        <p style={{ fontWeight: "var(--font-weight-semibold)", margin: 0 }}>{title ?? "Couldn't load this data"}</p>
        <p style={{ margin: "0.25rem 0 0", fontSize: "var(--font-size-sm)" }}>{message}</p>
        {correlationId !== undefined && (
          <p style={{ margin: "0.25rem 0 0", fontSize: "var(--font-size-xs)", opacity: 0.75 }}>
            Status {correlationId} — data may have changed since your last view.
          </p>
        )}
        {onRetry && (
          <Button variant="secondary" size="small" onClick={onRetry} style={{ marginTop: "var(--space-3)" }}>
            <RefreshCw size={14} aria-hidden /> Retry
          </Button>
        )}
      </div>
    </div>
  );
}
