"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function ProjectIndexPage() {
  const router = useRouter();
  const params = useParams<{ projectId: string }>();

  useEffect(() => {
    router.replace(`/app/projects/${params.projectId}/overview`);
  }, [router, params.projectId]);

  return null;
}
