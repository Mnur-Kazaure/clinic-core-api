// clinic-app/src/app/cmd/components/CmdSidebar.tsx
'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { usePathname } from 'next/navigation';

interface CmdSidebarProps {
  clinicName: string;
}

const menuGroups = [
  {
    title: 'Command & Control',
    items: [
      { label: 'CMD Command Center', href: '/cmd' },
    ],
  },
  {
    title: 'Patient Operations',
    items: [
      { label: 'Overview', href: '/cmd/patient-operations' },
      { label: 'Outpatients', href: '/cmd/outpatients' },
      { label: 'Inpatients', href: '/cmd/inpatients' },
      { label: 'Follow-Ups', href: '/cmd/follow-ups' },
      { label: 'Emergency Cases', href: '/cmd/emergency' },
    ],
  },
  {
    title: 'Finance & Revenue',
    items: [
      { label: 'Revenue & Payments', href: '/cmd/revenue' },
    ],
  },
  {
    title: 'Staff & Security',
    items: [
      { label: 'Staff & Biometrics', href: '/cmd/attendance' },
      { label: 'Audit & Traceability', href: '/cmd/audit' },
      { label: 'Roles & Permissions', href: '/cmd/roles' },
      { label: 'Security Center', href: '/cmd/security' },
    ],
  },
  {
    title: 'Intelligence & Health',
    items: [
      { label: 'Executive Analytics', href: '/cmd/analytics' },
      { label: 'Reports Center', href: '/cmd/reports' },
      { label: 'System Health', href: '/cmd/health' },
    ],
  },
  {
    title: 'System',
    items: [
      { label: 'Settings', href: '/cmd/settings' },
    ],
  },
];

export function CmdSidebar({ clinicName }: CmdSidebarProps) {
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
      <div className="border-b border-indigo-100 bg-slate-50 px-5 py-6">
        <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-indigo-600">
          CHIEF MEDICAL DIRECTOR
        </p>
        <h2 className="mt-2 text-lg font-bold text-slate-900 leading-tight">
          {clinicName}
        </h2>
        <p className="mt-2 text-[11px] text-slate-500 font-medium italic">
          Full Directive & Analytical Oversight
        </p>
      </div>

      <nav className="flex-1 space-y-6 px-4 py-6 overflow-y-auto">
        {menu.map((group) => (
          <div key={group.title}>
            <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              {group.title}
            </p>
            <div className="space-y-1">
              {group.items.map((item) => {
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.label}
                    href={item.href}
                    className={`flex items-center justify-between rounded-md px-3 py-2 text-sm font-semibold transition-all duration-200 ${
                      active
                        ? 'bg-indigo-600 text-white shadow-md shadow-indigo-100'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-indigo-600'
                    }`}
                  >
                    <span>{item.label}</span>
                    {active && (
                      <div className="h-1 w-1 rounded-full bg-white opacity-50"></div>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
      
      <div className="p-4 border-t border-slate-100 bg-slate-50">
        <div className="rounded-lg bg-indigo-50 p-3">
          <p className="text-[10px] font-bold text-indigo-700 uppercase tracking-tighter">Secure Session</p>
          <p className="mt-1 text-[11px] text-indigo-600 leading-snug font-medium">
            Biometric integrity enabled. All directives are audit-sealed.
          </p>
        </div>
      </div>
    </div>
  );
}
