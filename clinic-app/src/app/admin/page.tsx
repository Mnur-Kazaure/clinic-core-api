// clinic-app/src/app/admin/page.tsx

'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ClinicProfileForm } from './components/ClinicProfileForm';
import { AdminQuickActions } from './components/AdminQuickActions';
import { StaffDirectory } from './components/StaffDirectory';
import { ClinicSettingsForm } from './components/ClinicSettingsForm';
import { Card } from '@/shared/Card';
import { PaymentOversightCard } from './components/PaymentOversightCard';
import { PatientRegistrationMetrics } from './components/PatientRegistrationMetrics';
import { DashboardHero } from '@/app/components/DashboardHero';
import {
  getDashboardUserDisplayName,
  useDashboardUser,
} from '@/app/components/DashboardUserContext';
import { HOSPITAL_NAME } from '@/shared/constants/branding';
import {
  pharmacyCatalogGovernanceService,
  type PharmacyCatalogRegistryRow,
} from '@/domains/pharmacy/services/pharmacyCatalogGovernanceService';

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
  const dashboardUser = useDashboardUser();
  const [pharmacyCatalog, setPharmacyCatalog] = useState<PharmacyCatalogRegistryRow[]>([]);

  useEffect(() => {
    void pharmacyCatalogGovernanceService
      .listAdminCatalogRegistry()
      .then(setPharmacyCatalog)
      .catch(() => setPharmacyCatalog([]));
  }, []);

  return (
    <div className="space-y-8">
      <section
        id="overview"
        className="rounded-2xl"
      >
        <DashboardHero
          title="Clinic Admin Dashboard"
          subtitle={HOSPITAL_NAME}
          workspaceLabel="Operational visibility, staff oversight, and compliance signals in one view"
          monogram="K"
          rightSlot={
            <>
              <div>
                <span className="font-semibold">Administrator:</span>{' '}
                {getDashboardUserDisplayName(dashboardUser)}
              </div>
              <div>Clinic Governance</div>
            </>
          }
          actionsSlot={
            <>
              <Link
                href="/admin/service-lines"
                className="inline-flex items-center justify-center rounded-lg border border-white/40 bg-white/10 px-4 py-2 text-sm font-medium text-white hover:bg-white/20"
              >
                Service Lines
              </Link>
              <Link
                href="/admin/settings"
                className="inline-flex items-center justify-center rounded-lg border border-white/40 bg-white/10 px-4 py-2 text-sm font-medium text-white hover:bg-white/20"
              >
                Open Settings
              </Link>
            </>
          }
        />
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

      <section id="pharmacy-catalog">
        <Card title="Pharmacy Catalog Governance Registry">
          {pharmacyCatalog.length === 0 ? (
            <p className="text-sm text-slate-500">No pharmacy catalog items have been governed yet.</p>
          ) : (
            <div className="space-y-3">
              {pharmacyCatalog.slice(0, 12).map((item) => (
                <div
                  key={item.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 px-4 py-3 text-sm"
                >
                  <div>
                    <p className="font-medium text-slate-900">
                      {item.generic_name}
                      {item.strength ? ` ${item.strength}` : ''} {item.dosage_form}
                    </p>
                    <p className="text-slate-500">
                      {item.catalog_code} • {item.lifecycle_status} • Billing {item.billing_status}
                    </p>
                  </div>
                  <div className="text-right text-slate-500">
                    <p>{item.requested_by_name || 'Unknown requester'}</p>
                    <p>{item.charge_code || 'Charge pending'}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </section>
    </div>
  );
}
