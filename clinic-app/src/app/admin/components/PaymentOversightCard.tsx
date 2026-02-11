'use client';

import { Card } from '@/shared/Card';

export function PaymentOversightCard() {
  return (
    <Card title="Payment Oversight (Read-only)">
      <div className="space-y-3 text-sm text-slate-600">
        <p>
          Live payment analytics will appear here once the backend feeds are
          enabled. Until then, this panel remains read-only with no cached
          metrics.
        </p>
        <ul className="list-disc space-y-1 pl-5 text-slate-500">
          <li>Revenue overview and collection rate</li>
          <li>Live transaction feed</li>
          <li>Revenue by service category</li>
          <li>Outstanding balances summary</li>
        </ul>
      </div>
    </Card>
  );
}
