"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function SettingsIndexPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/app/settings/profile");
  }, [router]);
  return null;
}
