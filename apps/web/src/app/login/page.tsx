"use client";

import { AlertCircle, ArrowRight, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Field";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail ?? err.message) : "Login failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen grid-cols-1 md:grid-cols-[minmax(0,1fr)_26rem]">
      <BrandPanel />

      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "var(--space-6)", background: "var(--surface-page)" }}>
        <div className="animate-fade-in-up" style={{ width: "100%", maxWidth: "22rem" }}>
          <h1 style={{ margin: "0 0 var(--space-1)", fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-semibold)" }}>
            Sign in to your workspace
          </h1>
          <p style={{ margin: "0 0 var(--space-6)", color: "var(--text-secondary)", fontSize: "var(--font-size-sm)" }}>
            Evidence-backed answers for every project question.
          </p>

          <form onSubmit={handleSubmit} style={{ display: "grid", gap: "var(--space-4)" }}>
            {error && (
              <div className="error-state" style={{ padding: "var(--space-3)" }}>
                <AlertCircle size={16} aria-hidden style={{ flexShrink: 0 }} />
                <p style={{ margin: 0, fontSize: "var(--font-size-sm)" }}>{error}</p>
              </div>
            )}

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

            <Field label="Password" htmlFor="password">
              <Input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>

            <Button type="submit" loading={submitting} fullWidth size="large">
              Sign in <ArrowRight size={16} aria-hidden />
            </Button>
          </form>

          <p style={{ marginTop: "var(--space-3)", fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
            Forgot your password? Ask your workspace administrator to reset it from Team settings.
          </p>

          <p style={{ marginTop: "var(--space-6)", textAlign: "center", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)" }}>
            No workspace yet?{" "}
            <Link href="/register" style={{ fontWeight: "var(--font-weight-medium)" }}>
              Create one
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}

function BrandPanel() {
  return (
    <div
      className="hidden md:flex"
      style={{
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "var(--space-10)",
        background: `linear-gradient(160deg, var(--color-brand-950), var(--color-brand-900) 55%, var(--color-brand-800))`,
        color: "#fff",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
        <span className="sidebar-brand__mark" style={{ width: "2.5rem", height: "2.5rem" }}>
          A
        </span>
        <span style={{ fontWeight: "var(--font-weight-bold)", fontSize: "var(--font-size-lg)" }}>AtlasAI</span>
      </div>

      <div style={{ maxWidth: "30rem" }}>
        <h2 style={{ fontSize: "var(--font-size-4xl)", lineHeight: "var(--line-height-tight)", letterSpacing: "-0.02em", margin: "0 0 var(--space-4)" }}>
          Evidence, clarity, progress.
        </h2>
        <p style={{ color: "rgba(255,255,255,0.75)", fontSize: "var(--font-size-md)", lineHeight: "var(--line-height-relaxed)" }}>
          Every scope question answered with cited evidence, verified conflicts, and a traceable decision trail — never a guess dressed up as fact.
        </p>

        <div style={{ marginTop: "var(--space-8)", display: "grid", gap: "var(--space-3)" }}>
          <Feature icon={Sparkles} text="AI investigations grounded in your project's own evidence" />
          <Feature icon={ShieldCheck} text="Human approval required before any client-facing action" />
        </div>
      </div>

      <p style={{ color: "rgba(255,255,255,0.4)", fontSize: "var(--font-size-xs)" }}>
        © {new Date().getFullYear()} AtlasAI. Secured, permission-filtered evidence access.
      </p>
    </div>
  );
}

function Feature({ icon: Icon, text }: { icon: typeof Sparkles; text: string }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: "var(--space-3)" }}>
      <span
        style={{
          display: "grid",
          placeItems: "center",
          width: "1.75rem",
          height: "1.75rem",
          flexShrink: 0,
          borderRadius: "var(--radius-md)",
          background: "rgba(255,255,255,0.1)",
        }}
      >
        <Icon size={14} aria-hidden />
      </span>
      <span style={{ fontSize: "var(--font-size-sm)", color: "rgba(255,255,255,0.85)" }}>{text}</span>
    </div>
  );
}
