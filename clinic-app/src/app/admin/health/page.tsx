'use client';

import Link from 'next/link';
import { ClinicHealthSnapshot } from '../components/ClinicHealthSnapshot';
import { ShiftCoverageSnapshot } from '../components/ShiftCoverageSnapshot';

export default function AdminHealthPage() {
  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <div className="flex flex-col gap-3">
          <Link href="/admin" className="text-sm text-slate-500 hover:text-slate-700">
            ← Back to Admin Dashboard
          </Link>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">System Health</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">Clinic Health & Coverage</h1>
            <p className="mt-2 text-sm text-slate-600">
              Live operational signals for staffing and patient flow readiness.
            </p>
          </div>
        </div>
      </section>

      <section>
        <ClinicHealthSnapshot />
      </section>

      <section>
        <ShiftCoverageSnapshot />
      </section>
    </div>
  );
}
