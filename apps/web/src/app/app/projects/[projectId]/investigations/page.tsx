"use client";

import { Sparkles } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { useAgentRuns, useCreateAgentRun } from "@/hooks/useAgentRuns";
import { ApiError } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";
import { agentRunStatusDisplay } from "@/lib/status";
import { PageHeader } from "@/components/shell/PageHeader";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Textarea } from "@/components/ui/Field";
import { SkeletonLines } from "@/components/ui/Skeleton";

const SUGGESTED_QUESTIONS = [
  "Was this feature included in the agreed scope?",
  "When was this requirement approved?",
  "Is this feature delivered or only discussed?",
  "Are there conflicting statements across emails and meetings?",
  "What evidence supports the current project status?",
];

export default function InvestigationsPage() {
  const params = useParams<{ projectId: string }>();
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [error, setError] = useState<string | null>(null);
  const createRun = useCreateAgentRun(params.projectId);
  const { data: runs, isLoading, error: listError, refetch } = useAgentRuns(params.projectId);

  async function handleSubmit() {
    if (!question.trim() || createRun.isPending) return;
    setError(null);
    try {
      const run = await createRun.mutateAsync(question.trim());
      router.push(`/app/projects/${params.projectId}/investigations/${run.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail ?? err.message) : "Could not start the investigation.");
    }
  }

  return (
    <div>
      <PageHeader
        title="Investigations"
        description="Ask a project-truth question. AtlasAI retrieves permission-filtered evidence, analyzes it, and produces a cited finding."
      />

      <div className="card" style={{ padding: "var(--space-5)", marginBottom: "var(--space-6)" }}>
        {error && (
          <div className="error-state" style={{ marginBottom: "var(--space-3)" }}>
            <p style={{ margin: 0, fontSize: "var(--font-size-sm)" }}>{error}</p>
          </div>
        )}
        <Textarea
          placeholder="e.g. Is the analytics dashboard included in Phase 1?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              void handleSubmit();
            }
          }}
        />
        <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", marginTop: "var(--space-3)" }}>
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              className="badge badge--neutral"
              style={{ cursor: "pointer", border: "none" }}
              onClick={() => setQuestion(q)}
            >
              {q}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "var(--space-4)" }}>
          <Button onClick={handleSubmit} loading={createRun.isPending} disabled={!question.trim()}>
            <Sparkles size={16} aria-hidden /> Run investigation
          </Button>
        </div>
      </div>

      <h2 style={{ fontSize: "var(--font-size-lg)", fontWeight: "var(--font-weight-semibold)", marginBottom: "var(--space-3)" }}>
        History
      </h2>

      {listError ? (
        <ErrorState error={listError} onRetry={() => refetch()} />
      ) : isLoading ? (
        <SkeletonLines count={4} />
      ) : !runs || runs.length === 0 ? (
        <EmptyState icon={Sparkles} title="No investigations yet" description="Ask your first question above to get started." />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Status</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              {runs
                .slice()
                .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                .map((run) => (
                  <tr
                    key={run.id}
                    className="is-clickable"
                    onClick={() => router.push(`/app/projects/${params.projectId}/investigations/${run.id}`)}
                  >
                    <td style={{ maxWidth: "32rem" }}>{run.question}</td>
                    <td>
                      <StatusBadge status={agentRunStatusDisplay(run.status)} />
                    </td>
                    <td>{formatRelativeTime(run.created_at)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
