"use client";

import { useParams } from "next/navigation";

import { ProjectTasksView } from "@/components/requirements/ProjectTasksView";

export default function RequirementsListPage() {
  const params = useParams<{ projectId: string }>();
  return <ProjectTasksView projectId={params.projectId} />;
}
