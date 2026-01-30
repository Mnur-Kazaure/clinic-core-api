'use client';

import { ClinicProfileForm } from './components/ClinicProfileForm';
import { StaffDirectory } from './components/StaffDirectory';

export default function AdminPage() {
  return (
    <div className="space-y-10">
      <section
        id="overview"
        className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm"
      >
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
              Clinic Governance
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">
              Clinic Admin Dashboard
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              Manage clinic profile, staff credentials, and operational
              readiness with audit-grade precision.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-sm">
            <p className="font-medium text-slate-900">Today’s focus</p>
            <ul className="mt-2 space-y-1">
              <li>Verify doctor availability and room assignments.</li>
              <li>Audit staff roles before morning shift.</li>
              <li>Keep clinic profile accurate for compliance.</li>
            </ul>
          </div>
        </div>
      </section>

      <section id="clinic-profile" className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <ClinicProfileForm />
        </div>
        <div className="lg:col-span-1 space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">
              Governance Notes
            </h2>
            <ul className="mt-3 space-y-2 text-sm text-slate-600">
              <li>Ensure all staff have correct roles before shifts.</li>
              <li>Doctor profiles should include specialty, department, room.</li>
              <li>Disabling a staff account blocks access immediately.</li>
            </ul>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-900 p-5 text-sm text-slate-100 shadow-sm">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
              Compliance
            </p>
            <p className="mt-2 font-semibold">Identity authority</p>
            <p className="mt-2 text-slate-300">
              Clinic profile and staff credentials are authoritative records.
              Keep them up to date for audit readiness.
            </p>
          </div>
        </div>
      </section>

      <section id="staff-directory">
        <StaffDirectory />
      </section>
    </div>
  );
}
