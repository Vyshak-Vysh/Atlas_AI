"use client";

import { AlertCircle, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Field";

export default function RegisterPage() {
  const { register } = useAuth();
  const [tenantName, setTenantName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(tenantName, email, password, displayName);
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail ?? err.message) : "Registration failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4" style={{ background: "var(--surface-page)" }}>
      <div className="animate-fade-in-up card" style={{ width: "100%", maxWidth: "26rem", padding: "var(--space-8)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-6)" }}>
          <span className="sidebar-brand__mark">A</span>
          <span style={{ fontWeight: "var(--font-weight-bold)", fontSize: "var(--font-size-lg)" }}>AtlasAI</span>
        </div>

        <h1 style={{ margin: "0 0 var(--space-1)", fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-semibold)" }}>
          Create your workspace
        </h1>
        <p style={{ margin: "0 0 var(--space-6)", color: "var(--text-secondary)", fontSize: "var(--font-size-sm)" }}>
          This creates a new tenant and makes you its administrator.
        </p>

        <form onSubmit={handleSubmit} style={{ display: "grid", gap: "var(--space-4)" }}>
          {error && (
            <div className="error-state" style={{ padding: "var(--space-3)" }}>
              <AlertCircle size={16} aria-hidden style={{ flexShrink: 0 }} />
              <p style={{ margin: 0, fontSize: "var(--font-size-sm)" }}>{error}</p>
            </div>
          )}

          <Field label="Company / workspace name" htmlFor="tenantName">
            <Input id="tenantName" required value={tenantName} onChange={(e) => setTenantName(e.target.value)} />
          </Field>

          <Field label="Your name" htmlFor="displayName">
            <Input id="displayName" required value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </Field>

          <Field label="Email" htmlFor="email">
            <Input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>

          <Field label="Password" htmlFor="password" hint="At least 10 characters.">
            <Input
              id="password"
              type="password"
              required
              minLength={10}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>

          <Button type="submit" loading={submitting} fullWidth size="large">
            Create workspace <ArrowRight size={16} aria-hidden />
          </Button>
        </form>

        <p style={{ marginTop: "var(--space-5)", textAlign: "center", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)" }}>
          Already have a workspace?{" "}
          <Link href="/login" style={{ fontWeight: "var(--font-weight-medium)" }}>
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
