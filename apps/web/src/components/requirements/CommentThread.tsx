"use client";

import { useState } from "react";

import {
  useAddRequirementComment,
  useDeleteRequirementComment,
  useRequirementComments,
  useUpdateRequirementComment,
} from "@/hooks/useRequirements";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useCurrentRole } from "@/hooks/useCurrentWorkspace";
import { formatRelativeTime } from "@/lib/format";
import { roleHasPermission } from "@/lib/permissions";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Textarea } from "@/components/ui/Field";
import { MessageSquare } from "lucide-react";

export function CommentThread({ requirementId, projectId }: { requirementId: string; projectId: string }) {
  const role = useCurrentRole();
  const { data: me } = useCurrentUser();
  const { data: comments, isLoading } = useRequirementComments(requirementId, projectId);
  const addComment = useAddRequirementComment(requirementId, projectId);
  const [draft, setDraft] = useState("");

  const canComment = roleHasPermission(role, "COMMENT_ON_TASK");

  async function handleSubmit() {
    if (!draft.trim()) return;
    await addComment.mutateAsync(draft.trim());
    setDraft("");
  }

  return (
    <div style={{ display: "grid", gap: "var(--space-4)" }}>
      {canComment && (
        <div style={{ display: "grid", gap: "var(--space-2)" }}>
          <Textarea
            rows={3}
            placeholder="Add a comment…"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <Button size="small" onClick={handleSubmit} loading={addComment.isPending} disabled={!draft.trim()}>
              Comment
            </Button>
          </div>
        </div>
      )}

      {isLoading ? (
        <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-tertiary)" }}>Loading comments…</p>
      ) : !comments || comments.length === 0 ? (
        <EmptyState icon={MessageSquare} title="No comments yet" description="Start the conversation on this task." />
      ) : (
        <div style={{ display: "grid", gap: "var(--space-3)" }}>
          {comments.map((comment) => (
            <CommentItem
              key={comment.id}
              requirementId={requirementId}
              projectId={projectId}
              comment={comment}
              canModerate={comment.author_id === me?.id || role === "AI_ENGINEER_ADMIN"}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CommentItem({
  requirementId,
  projectId,
  comment,
  canModerate,
}: {
  requirementId: string;
  projectId: string;
  comment: { id: string; author_display_name: string; body: string; created_at: string; updated_at: string };
  canModerate: boolean;
}) {
  const updateComment = useUpdateRequirementComment(requirementId, projectId);
  const deleteComment = useDeleteRequirementComment(requirementId, projectId);
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(comment.body);

  async function handleSave() {
    if (!body.trim()) return;
    await updateComment.mutateAsync({ commentId: comment.id, body: body.trim() });
    setEditing(false);
  }

  return (
    <div style={{ display: "flex", gap: "var(--space-3)" }}>
      <Avatar name={comment.author_display_name} size={28} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "var(--space-2)" }}>
          <span style={{ fontSize: "var(--font-size-sm)", fontWeight: "var(--font-weight-semibold)" }}>
            {comment.author_display_name}
          </span>
          <span style={{ fontSize: "var(--font-size-2xs)", color: "var(--text-tertiary)" }}>
            {formatRelativeTime(comment.created_at)}
            {comment.updated_at !== comment.created_at ? " · edited" : ""}
          </span>
        </div>
        {editing ? (
          <div style={{ display: "grid", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
            <Textarea rows={2} value={body} onChange={(e) => setBody(e.target.value)} />
            <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
              <Button variant="secondary" size="small" onClick={() => setEditing(false)}>
                Cancel
              </Button>
              <Button size="small" onClick={handleSave} loading={updateComment.isPending}>
                Save
              </Button>
            </div>
          </div>
        ) : (
          <p style={{ margin: "var(--space-1) 0 0", fontSize: "var(--font-size-sm)", lineHeight: "var(--line-height-relaxed)" }}>
            {comment.body}
          </p>
        )}
        {canModerate && !editing && (
          <div style={{ display: "flex", gap: "var(--space-3)", marginTop: "var(--space-1)" }}>
            <button type="button" className="link-button" onClick={() => setEditing(true)}>
              Edit
            </button>
            <button
              type="button"
              className="link-button"
              onClick={() => deleteComment.mutate(comment.id)}
              disabled={deleteComment.isPending}
            >
              Delete
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
