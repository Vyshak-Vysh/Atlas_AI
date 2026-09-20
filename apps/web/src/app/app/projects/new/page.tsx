"use client";

import { ArrowLeft, ArrowRight, Check, FileUp, Mail, MessageSquare } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { useSpaces } from "@/hooks/useSpaces";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/lib/toast";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Field, Input, Select } from "@/components/ui/Field";

interface PhaseDraft {
  name: string;
  phase_number: number;
}

const STEPS = ["Basic details", "Project structure", "Connect sources", "Review & create"] as const;

export default function NewProjectPage() {
  const { session } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const { data: spaces } = useSpaces();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [clientName, setClientName] = useState("");
  const [code, setCode] = useState("");
  const [spaceId, setSpaceId] = useState(searchParams.get("spaceId") ?? "");
  const [phases, setPhases] = useState<PhaseDraft[]>([{ name: "Phase 1", phase_number: 1 }]);
  const [connectManualUpload, setConnectManualUpload] = useState(true);

  function updatePhase(index: number, patch: Partial<PhaseDraft>) {
    setPhases((current) => current.map((p, i) => (i === index ? { ...p, ...patch } : p)));
  }

  function addPhase() {
    setPhases((current) => [...current, { name: "", phase_number: current.length + 1 }]);
  }

  function removePhase(index: number) {
    setPhases((current) => current.filter((_, i) => i !== index));
  }

  const canContinue = step === 0 ? name.trim().length > 0 : true;

  async function handleCreate() {
    if (!session) return;
    setSubmitting(true);
    setError(null);
    try {
      const project = await api.createProject({
        tenant_id: session.tenantId,
        name: name.trim(),
        client_name: clientName.trim() || undefined,
        code: code.trim() || undefined,
        space_id: spaceId || undefined,
      });

      for (const phase of phases) {
        if (!phase.name.trim()) continue;
        await api.createPhase(project.id, { name: phase.name.trim(), phase_number: phase.phase_number });
      }

      if (connectManualUpload) {
        try {
          await api.createConnector({ tenant_id: session.tenantId, project_id: project.id, provider: "MANUAL_UPLOAD" });
        } catch {
          // Non-fatal — the connector is also lazily created on first upload.
        }
      }

      toast({ title: "Project created", description: `${project.name} is ready.`, variant: "success" });
      router.push(`/app/projects/${project.id}/overview`);
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail ?? err.message) : "Failed to create project.");
      setSubmitting(false);
    }
  }

  return (
    <div style={{ maxWidth: "42rem", margin: "0 auto" }}>
      <PageHeader title="Create a project" description="Set up a new evidence-backed project workspace." />

      <div style={{ display: "flex", gap: "var(--space-2)", marginBottom: "var(--space-6)" }}>
        {STEPS.map((label, i) => (
          <div key={label} style={{ flex: 1, textAlign: "center" }}>
            <div
              style={{
                margin: "0 auto var(--space-2)",
                width: "1.75rem",
                height: "1.75rem",
                borderRadius: "var(--radius-full)",
                display: "grid",
                placeItems: "center",
                fontSize: "var(--font-size-xs)",
                fontWeight: "var(--font-weight-semibold)",
                background: i <= step ? "var(--color-brand-600)" : "var(--surface-muted)",
                color: i <= step ? "#fff" : "var(--text-tertiary)",
                transition: "background var(--motion-normal) var(--motion-ease)",
              }}
            >
              {i < step ? <Check size={14} aria-hidden /> : i + 1}
            </div>
            <span style={{ fontSize: "var(--font-size-xs)", color: i === step ? "var(--text-primary)" : "var(--text-tertiary)" }}>
              {label}
            </span>
          </div>
        ))}
      </div>

      <Card>
        <CardBody>
          {error && (
            <div className="error-state" style={{ marginBottom: "var(--space-4)" }}>
              <p style={{ margin: 0, fontSize: "var(--font-size-sm)" }}>{error}</p>
            </div>
          )}

          {step === 0 && (
            <div style={{ display: "grid", gap: "var(--space-4)" }}>
              <Field label="Project name" htmlFor="name">
                <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} placeholder="Client Portal Revamp" />
              </Field>
              <Field label="Client name" htmlFor="clientName">
                <Input id="clientName" value={clientName} onChange={(e) => setClientName(e.target.value)} placeholder="Acme Corporation" />
              </Field>
              <Field label="Project code" htmlFor="code" hint="Optional short identifier, e.g. ACME-01.">
                <Input id="code" value={code} onChange={(e) => setCode(e.target.value)} />
              </Field>
              <Field label="Space" htmlFor="spaceId" hint="Optional — group this project under a Space.">
                <Select id="spaceId" value={spaceId} onChange={(e) => setSpaceId(e.target.value)}>
                  <option value="">No space</option>
                  {(spaces ?? []).map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
          )}

          {step === 1 && (
            <div style={{ display: "grid", gap: "var(--space-4)" }}>
              <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--text-secondary)" }}>
                Add the initial phases for this project. You can add more later from the project overview.
              </p>
              {phases.map((phase, i) => (
                <div key={i} style={{ display: "flex", gap: "var(--space-2)" }}>
                  <Input
                    type="number"
                    min={1}
                    value={phase.phase_number}
                    onChange={(e) => updatePhase(i, { phase_number: Number(e.target.value) })}
                    style={{ maxWidth: "5rem" }}
                    aria-label={`Phase ${i + 1} number`}
                  />
                  <Input
                    value={phase.name}
                    onChange={(e) => updatePhase(i, { name: e.target.value })}
                    placeholder="Phase name"
                    aria-label={`Phase ${i + 1} name`}
                  />
                  <Button variant="ghost" size="small" onClick={() => removePhase(i)} aria-label="Remove phase">
                    ✕
                  </Button>
                </div>
              ))}
              <Button variant="secondary" size="small" onClick={addPhase} style={{ justifySelf: "start" }}>
                + Add phase
              </Button>
            </div>
          )}

          {step === 2 && (
            <div style={{ display: "grid", gap: "var(--space-3)" }}>
              <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--text-secondary)" }}>
                Only manual upload is available to connect automatically in this deployment. Email, calendar, and PM
                connectors require an administrator to configure OAuth credentials first — you can request that from
                Connectors once the project exists.
              </p>
              <label
                className="card"
                style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", padding: "var(--space-4)", cursor: "pointer" }}
              >
                <input type="checkbox" checked={connectManualUpload} onChange={(e) => setConnectManualUpload(e.target.checked)} />
                <FileUp size={18} aria-hidden style={{ color: "var(--color-brand-700)" }} />
                <div>
                  <p style={{ margin: 0, fontWeight: "var(--font-weight-medium)" }}>Manual upload</p>
                  <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
                    Upload documents directly — PDF, DOCX, XLSX, images (OCR).
                  </p>
                </div>
              </label>
              {[
                { icon: Mail, label: "Gmail / Microsoft 365" },
                { icon: MessageSquare, label: "Meeting transcripts" },
              ].map(({ icon: Icon, label }) => (
                <div
                  key={label}
                  className="card"
                  style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", padding: "var(--space-4)", opacity: 0.6 }}
                >
                  <Icon size={18} aria-hidden />
                  <div>
                    <p style={{ margin: 0, fontWeight: "var(--font-weight-medium)" }}>{label}</p>
                    <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
                      Not configured for this deployment yet
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {step === 3 && (
            <div style={{ display: "grid", gap: "var(--space-3)", fontSize: "var(--font-size-sm)" }}>
              <SummaryRow label="Name" value={name} />
              <SummaryRow label="Client" value={clientName || "—"} />
              <SummaryRow label="Code" value={code || "—"} />
              <SummaryRow label="Space" value={spaces?.find((s) => s.id === spaceId)?.name ?? "None"} />
              <SummaryRow label="Phases" value={phases.filter((p) => p.name.trim()).map((p) => p.name).join(", ") || "None"} />
              <SummaryRow label="Sources" value={connectManualUpload ? "Manual upload" : "None yet"} />
              <SummaryRow label="Your role" value="AI Engineer Admin (project creator)" />
            </div>
          )}
        </CardBody>
      </Card>

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: "var(--space-5)" }}>
        <Button variant="secondary" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
          <ArrowLeft size={16} aria-hidden /> Back
        </Button>
        {step < STEPS.length - 1 ? (
          <Button onClick={() => setStep((s) => s + 1)} disabled={!canContinue}>
            Continue <ArrowRight size={16} aria-hidden />
          </Button>
        ) : (
          <Button onClick={handleCreate} loading={submitting}>
            Create project
          </Button>
        )}
      </div>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: "var(--space-3)", paddingBottom: "var(--space-2)", borderBottom: "1px solid var(--border-subtle)" }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ fontWeight: "var(--font-weight-medium)", textAlign: "right" }}>{value}</span>
    </div>
  );
}
