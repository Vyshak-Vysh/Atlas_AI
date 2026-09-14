"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { TaskDetailContent } from "@/components/requirements/TaskDetailContent";

export default function RequirementDetailPage() {
  const params = useParams<{ projectId: string; requirementId: string }>();
  const router = useRouter();

  return (
    <div style={{ maxWidth: "44rem" }}>
      <Link
        href={`/app/projects/${params.projectId}/requirements`}
        style={{ display: "inline-block", marginBottom: "var(--space-4)", fontSize: "var(--font-size-sm)" }}
      >
        ← All tasks
      </Link>

      <TaskDetailContent
        key={params.requirementId}
        requirementId={params.requirementId}
        projectId={params.projectId}
        onDeleted={() => router.push(`/app/projects/${params.projectId}/requirements`)}
      />
    </div>
  );
}
