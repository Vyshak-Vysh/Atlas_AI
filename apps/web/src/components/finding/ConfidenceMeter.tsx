import { cn } from "@/lib/cn";
import { formatPercent } from "@/lib/format";

export function ConfidenceMeter({ confidence }: { confidence: number | null }) {
  if (confidence === null) {
    return <p style={{ color: "var(--text-tertiary)", fontSize: "var(--font-size-sm)" }}>Confidence not available</p>;
  }

  const level = confidence >= 0.75 ? "high" : confidence >= 0.45 ? "medium" : "low";

  return (
    <div>
      <div className="confidence-meter">
        <div
          className={cn("confidence-meter__value", `confidence-meter__value--${level}`)}
          style={{ width: `${Math.round(confidence * 100)}%` }}
        />
      </div>
      <p style={{ marginTop: "var(--space-2)", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)" }}>
        {formatPercent(confidence)} confidence
        {level === "low" && " — treat as a lead, not a conclusion"}
      </p>
    </div>
  );
}
