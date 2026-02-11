'use client';

import Link from 'next/link';
import { AuditTimeline } from '../components/AuditTimeline';
import { ComplianceSummary } from '../components/ComplianceSummary';

export default function AdminReportsPage() {
  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <div className="flex flex-col gap-3">
          <Link href="/admin" className="text-sm text-slate-500 hover:text-slate-700">
            ← Back to Admin Dashboard
          </Link>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Reports</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">Audit & Compliance Reports</h1>
            <p className="mt-2 text-sm text-slate-600">
              Track audit events, access patterns, and compliance exceptions.
            </p>
          </div>
        </div>
      </section>

      <section>
        <ComplianceSummary />
      </section>

      <section>
        <AuditTimeline />
      </section>
    </div>
  );
}
