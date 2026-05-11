'use client';

import Link from 'next/link';
import { ServiceLineGovernance } from '../components/ServiceLineGovernance';

export default function AdminServiceLinesPage() {
  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-3">
          <Link
            href="/admin"
            className="text-sm text-slate-500 hover:text-slate-700"
          >
            ← Back to Admin Dashboard
          </Link>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
              Service Governance
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">
              Service Lines & Department Mapping
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              Configure service hierarchy, receptionist department context, and doctor scope.
            </p>
          </div>
        </div>
      </section>

      <section>
        <ServiceLineGovernance />
      </section>
    </div>
  );
}
