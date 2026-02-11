'use client';

import { Card } from '@/shared/Card';

const placeholderRows = Array.from({ length: 4 }).map((_, idx) => idx);

export default function PaymentsPage() {
  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
          Real-time payment oversight
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">
          Payment Command Center
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Live collections, outstanding balances, and revenue by service category.
        </p>
        <p className="mt-3 text-xs text-slate-500">
          Data feeds are pending backend enablement. This view will populate
          automatically once payment analytics are live.
        </p>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        {[
          "Today's Revenue",
          'Monthly Target',
          'Outstanding Balance',
          'Collection Rate',
        ].map((title) => (
          <Card key={title}>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
              {title}
            </p>
            <div className="mt-3 text-2xl font-semibold text-slate-900">—</div>
            <p className="mt-2 text-xs text-slate-500">Awaiting data feed</p>
          </Card>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card title="Live Transactions (Read-only)">
            <div className="space-y-3 text-sm text-slate-600">
              {placeholderRows.map((row) => (
                <div
                  key={row}
                  className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3"
                >
                  <span className="text-slate-500">Awaiting feed</span>
                  <span className="font-mono text-slate-400">—</span>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Revenue by Service Category">
            <div className="space-y-3 text-sm text-slate-600">
              {['Consultation', 'Diagnostics', 'Pharmacy', 'Procedures'].map(
                (label) => (
                  <div
                    key={label}
                    className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3"
                  >
                    <span>{label}</span>
                    <span className="font-mono text-slate-400">—</span>
                  </div>
                )
              )}
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="Payment Intelligence">
            <div className="space-y-2 text-sm text-slate-600">
              <p>No alerts configured yet.</p>
              <p className="text-xs text-slate-500">
                Alerts will appear when payment analytics are enabled.
              </p>
            </div>
          </Card>

          <Card title="Outstanding Balances">
            <div className="space-y-2 text-sm text-slate-600">
              {placeholderRows.map((row) => (
                <div
                  key={row}
                  className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3"
                >
                  <span className="text-slate-500">Awaiting feed</span>
                  <span className="font-mono text-slate-400">—</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
}
