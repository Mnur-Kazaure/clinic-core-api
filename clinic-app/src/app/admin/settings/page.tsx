'use client';

import Link from 'next/link';
import { ClinicSettingsForm } from '../components/ClinicSettingsForm';

export default function AdminSettingsPage() {
  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <div className="flex flex-col gap-3">
          <Link
            href="/admin"
            className="text-sm text-slate-500 hover:text-slate-700"
          >
            ← Back to Admin Dashboard
          </Link>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
              Settings
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">
              Clinic Settings
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              Configure operational defaults and billing policies.
            </p>
          </div>
        </div>
      </section>

      <section>
        <ClinicSettingsForm />
      </section>
    </div>
  );
}
