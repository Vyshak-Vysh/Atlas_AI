import { Info } from "lucide-react";

import { Card, CardBody } from "@/components/ui/Card";

export default function BillingSettingsPage() {
  return (
    <Card>
      <CardBody>
        <div className="info-callout">
          <Info size={16} aria-hidden style={{ flexShrink: 0 }} />
          <span>
            This deployment doesn&rsquo;t have billing configured — there is no subscription or usage-metering
            system wired up yet. This page is a placeholder rather than a working billing integration.
          </span>
        </div>
      </CardBody>
    </Card>
  );
}
