'use client';

import Link from 'next/link';
import { Card } from '@/shared/Card';

const actions = [
  { label: 'Clinic Profile', href: '/admin#clinic-profile' },
  { label: 'Staff Directory', href: '/admin#staff-directory' },
  { label: 'Payments', href: '/admin/payments' },
  { label: 'Settings', href: '/admin/settings' },
  { label: 'Audit Trail', href: '/admin/audit' },
  { label: 'Access Matrix', href: '/admin/access' },
  { label: 'Analytics', href: '/admin/analytics' },
  { label: 'System Health', href: '/admin/health' },
];

export function AdminQuickActions() {
  return (
    <Card title="Quick Actions" titleClassName="text-slate-900">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {actions.map((action) => (
          <Link
            key={action.label}
            href={action.href}
            className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 hover:border-blue-200 hover:text-blue-700"
          >
            {action.label}
          </Link>
        ))}
      </div>
    </Card>
  );
}
