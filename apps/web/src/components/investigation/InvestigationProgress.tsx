import { Check, Loader2, X } from "lucide-react";

import { AGENT_STATE_LABELS, AGENT_STEP_ORDER } from "@/lib/status";
import type { AgentStepEvent } from "@/lib/types";

export function InvestigationProgress({ steps, failed }: { steps: AgentStepEvent[]; failed: boolean }) {
  const highestReachedIndex = steps.reduce((max, step) => {
    const idx = AGENT_STEP_ORDER.indexOf(step.state_name);
    return idx > max ? idx : max;
  }, -1);

  return (
    <div className="progress-steps">
      {AGENT_STEP_ORDER.map((state, index) => {
        const isCurrent = index === highestReachedIndex;
        const done = index < highestReachedIndex || (isCurrent && state === "COMPLETE" && !failed);
        const stepFailed = failed && isCurrent;
        const active = isCurrent && !done && !stepFailed;

        const className = stepFailed
          ? "progress-step progress-step--failed"
          : done
            ? "progress-step progress-step--done"
            : active
              ? "progress-step progress-step--active"
              : "progress-step";

        return (
          <div key={state} className={className}>
            <span className="progress-step__icon">
              {stepFailed ? (
                <X size={12} aria-hidden />
              ) : done ? (
                <Check size={12} aria-hidden />
              ) : active ? (
                <Loader2 size={12} className="animate-spin" aria-hidden />
              ) : (
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "currentColor" }} />
              )}
            </span>
            {AGENT_STATE_LABELS[state] ?? state}
          </div>
        );
      })}
    </div>
  );
}
