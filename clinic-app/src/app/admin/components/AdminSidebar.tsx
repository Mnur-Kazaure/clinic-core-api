// clinic-app/src/app/admin/components/AdminSidebar.tsx
'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { usePathname } from 'next/navigation';

interface AdminSidebarProps {
  clinicName: string;
}

const menuGroups = [
  {
    title: 'Clinic Overview',
    items: [
      { label: 'Overview', href: '/admin#overview' },
      { label: 'Staff Management', href: '/admin#staff-directory' },
    ],
  },
  {
    title: 'Governance',
    items: [
      { label: 'Access Control', href: '/admin/access' },
      { label: 'Service Lines', href: '/admin/service-lines' },
      { label: 'Pharmacy Catalog', href: '/admin#pharmacy-catalog' },
      { label: 'Admission Requests', href: '/admin/admissions' },
      { label: 'Audit Log', href: '/admin/audit' },
      { label: 'System Settings', href: '/admin/settings' },
    ],
  },
  {
    title: 'Financial Oversight',
    items: [
      { label: 'Payments', href: '/admin/payments' },
      { label: 'Reports', href: '/admin/reports' },
    ],
  },
];

export function AdminSidebar({ clinicName }: AdminSidebarProps) {
  const menu = useMemo(() => menuGroups, []);
  const pathname = usePathname();
  const [hash, setHash] = useState('');

  useEffect(() => {
    const updateHash = () => {
      setHash(window.location.hash || '');
    };
    updateHash();
    window.addEventListener('hashchange', updateHash);
    return () => window.removeEventListener('hashchange', updateHash);
  }, []);

  const isActive = (href: string) => {
    if (href.includes('#')) {
      const [path, fragment] = href.split('#');
      return pathname === path && hash === `#${fragment}`;
    }
    return pathname === href;
  };

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-slate-200 px-5 py-6">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
          Clinic Admin
        </p>
        <h2 className="mt-2 text-lg font-semibold text-slate-900">
          {clinicName}
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Governance, staffing, and operational oversight.
        </p>
      </div>

      <nav className="flex-1 space-y-6 px-4 py-6">
        {menu.map((group) => (
          <div key={group.title}>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              {group.title}
            </p>
            <div className="space-y-1">
              {group.items.map((item) => {
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.label}
                    href={item.href}
                    className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition ${
                      active
                        ? 'bg-slate-900 text-white'
                        : 'text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </div>
  );
}
