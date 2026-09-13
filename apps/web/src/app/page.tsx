"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth-context";

export default function HomePage() {
  const { session, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(session ? "/app/overview" : "/login");
  }, [loading, session, router]);

  return (
    <main className="flex min-h-screen items-center justify-center">
      <p style={{ color: "var(--text-tertiary)", fontSize: "var(--font-size-sm)" }}>Loading AtlasAI…</p>
    </main>
  );
}
