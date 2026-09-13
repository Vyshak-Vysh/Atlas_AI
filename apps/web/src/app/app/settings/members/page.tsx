"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function SettingsMembersRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/app/team");
  }, [router]);
  return null;
}
