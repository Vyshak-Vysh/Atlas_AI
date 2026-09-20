import { ALL_ROLES, ROLE_LABELS, roleHasPermission, type Permission } from "@/lib/permissions";
import { Card, CardBody } from "@/components/ui/Card";

const PERMISSIONS: { key: Permission; label: string }[] = [
  { key: "VIEW_PROJECT", label: "View project" },
  { key: "VIEW_INTERNAL_EVIDENCE", label: "View internal-only evidence" },
  { key: "UPLOAD_DOCUMENT", label: "Upload documents" },
  { key: "CONNECT_SOURCE", label: "Connect sources" },
  { key: "SYNC_SOURCE", label: "Sync sources" },
  { key: "RUN_AGENT", label: "Run investigations" },
  { key: "APPROVE_ACTION", label: "Approve / reject actions" },
  { key: "MANAGE_CONNECTORS", label: "Manage connectors" },
  { key: "MANAGE_POLICIES", label: "Manage policies" },
  { key: "VIEW_AUDIT_LOG", label: "View audit log" },
  { key: "MANAGE_PROJECT_MEMBERS", label: "Manage project members" },
];

export default function RolesSettingsPage() {
  return (
    <Card>
      <CardBody>
        <p style={{ margin: "0 0 var(--space-4)", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)" }}>
          Roles are fixed for this deployment — the same six roles apply to both workspace and project membership.
          Assign roles from Team or a project&apos;s Settings tab.
        </p>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Permission</th>
                {ALL_ROLES.map((r) => (
                  <th key={r}>{ROLE_LABELS[r]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {PERMISSIONS.map((p) => (
                <tr key={p.key}>
                  <td>{p.label}</td>
                  {ALL_ROLES.map((r) => (
                    <td key={r} style={{ textAlign: "center" }}>
                      {roleHasPermission(r, p.key) ? (
                        <span style={{ color: "var(--color-success-600)" }}>✓</span>
                      ) : (
                        <span style={{ color: "var(--border-default)" }}>—</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardBody>
    </Card>
  );
}
