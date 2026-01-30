'use client';

import { useMemo } from 'react';

const menuItems = [
  { label: 'Overview', href: '#overview' },
  { label: 'Clinic Profile', href: '#clinic-profile' },
  { label: 'Staff Directory', href: '#staff-directory' },
  { label: 'Security & Access', href: '#security-access', disabled: true },
  { label: 'Audit Trail', href: '#audit-trail', disabled: true },
];

export function AdminSidebar() {
  const menu = useMemo(() => menuItems, []);

  return (
    <aside className="rounded-2xl border border-slate-200 bg-white/80 shadow-sm backdrop-blur">
      <div className="p-5">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
          Control Center
        </p>
        <h2 className="mt-2 text-lg font-semibold text-slate-900">
          Clinic Admin
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Governance, staffing, and clinical readiness at a glance.
        </p>
      </div>

      <nav className="px-3 pb-4">
        {menu.map((item) => (
          <a
            key={item.label}
            href={item.disabled ? undefined : item.href}
            className={`flex items-center justify-between rounded-xl px-3 py-2 text-sm font-medium transition ${
              item.disabled
                ? 'text-slate-400 cursor-not-allowed'
                : 'text-slate-700 hover:bg-slate-100'
            }`}
          >
            <span>{item.label}</span>
            {item.disabled && (
              <span className="text-[10px] uppercase tracking-wide">
                Soon
              </span>
            )}
          </a>
        ))}
      </nav>
    </aside>
  );
}
