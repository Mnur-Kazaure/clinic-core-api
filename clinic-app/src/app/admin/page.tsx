// clinic-app/src/app/admin/page.tsx

'use client';

import Link from 'next/link';
import { ClinicProfileForm } from './components/ClinicProfileForm';
import { AdminQuickActions } from './components/AdminQuickActions';
import { StaffDirectory } from './components/StaffDirectory';
import { ClinicSettingsForm } from './components/ClinicSettingsForm';
import { Card } from '@/shared/Card';
import { PaymentOversightCard } from './components/PaymentOversightCard';
import { PatientRegistrationMetrics } from './components/PatientRegistrationMetrics';

const statCards = [
  {
    title: "Today's Revenue",
    description: 'Awaiting payment feed',
  },
  {
    title: 'New Patients',
    description: 'Awaiting registration metrics',
  },
  {
    title: 'Active Staff',
    description: 'Awaiting staff activity feed',
  },
  {
    title: 'System Health',
    description: 'Awaiting health snapshot',
  },
];

export default function AdminPage() {
  return (
    <div className="space-y-8">
      <section
        id="overview"
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
              Clinic Governance
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">
              Clinic Admin Dashboard
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              Operational visibility, staff oversight, and compliance signals in one view.
            </p>
          </div>
          <Link
            href="/admin/settings"
            className="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:border-slate-300 hover:text-slate-900"
          >
            Open Settings
          </Link>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <Card key={stat.title}>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
              {stat.title}
            </p>
            <div className="mt-3 text-2xl font-semibold text-slate-900">—</div>
            <p className="mt-2 text-xs text-slate-500">{stat.description}</p>
          </Card>
        ))}
      </section>

      <section id="quick-actions">
        <AdminQuickActions />
      </section>

      <section id="patient-metrics">
        <PatientRegistrationMetrics />
      </section>

      <section id="payment-oversight">
        <PaymentOversightCard />
      </section>

      <section id="clinic-profile" className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ClinicProfileForm />
        <ClinicSettingsForm />
      </section>

      <section id="staff-directory">
        <StaffDirectory />
      </section>
    </div>
  );
}
