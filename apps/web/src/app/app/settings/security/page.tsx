import { CheckCircle2, MinusCircle } from "lucide-react";

import { Card, CardBody } from "@/components/ui/Card";

const ACTIVE_MEASURES = [
  "Passwords hashed and never logged or exposed via the API",
  "Short-lived JWT access tokens (15 min) with rotating, one-time-use refresh tokens",
  "Every source document scanned for malware before indexing",
  "Connector credentials stored as encrypted references, never in prompts or logs",
  "Role-based access enforced on every tenant- and project-scoped request",
  "Internal-only evidence is never exposed to client-facing roles",
  "Every sensitive action recorded in an immutable audit log",
  "External actions require explicit human approval, bound to a hash-locked payload",
];

const NOT_CONFIGURED = [
  "Single sign-on (SAML / OIDC)",
  "Two-factor authentication",
  "IP allowlisting",
  "Custom session timeout policy",
];

export default function SecuritySettingsPage() {
  return (
    <div style={{ display: "grid", gap: "var(--space-5)" }}>
      <Card>
        <CardBody>
          <h2 style={{ margin: "0 0 var(--space-4)", fontSize: "var(--font-size-md)", fontWeight: "var(--font-weight-semibold)" }}>
            Active in this deployment
          </h2>
          <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: "var(--space-2)" }}>
            {ACTIVE_MEASURES.map((m) => (
              <li key={m} style={{ display: "flex", gap: "var(--space-2)", fontSize: "var(--font-size-sm)" }}>
                <CheckCircle2 size={16} aria-hidden style={{ color: "var(--color-success-600)", flexShrink: 0, marginTop: "0.1rem" }} />
                {m}
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>

      <Card>
        <CardBody>
          <h2 style={{ margin: "0 0 var(--space-4)", fontSize: "var(--font-size-md)", fontWeight: "var(--font-weight-semibold)" }}>
            Not available in this deployment
          </h2>
          <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: "var(--space-2)" }}>
            {NOT_CONFIGURED.map((m) => (
              <li key={m} style={{ display: "flex", gap: "var(--space-2)", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)" }}>
                <MinusCircle size={16} aria-hidden style={{ color: "var(--text-tertiary)", flexShrink: 0, marginTop: "0.1rem" }} />
                {m}
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
