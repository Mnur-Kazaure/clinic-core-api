'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useRouter } from 'next/navigation';
import { authService } from '@/domains/auth/services/authService';

const tabs = [
  { label: 'Clinic Admin', href: '/admin' },
  { label: 'Analytics', href: '/admin/analytics' },
  { label: 'Payments', href: '/admin/payments' },
  { label: 'Reports', href: '/admin/reports' },
  { label: 'System Health', href: '/admin/health' },
];

export function AdminTopNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const isActive = (href: string) => pathname === href;

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await authService.logout();
      router.push('/login');
    } catch (error) {
      console.error('Logout failed:', error);
      setIsLoggingOut(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
      <nav className="flex flex-wrap gap-2">
        {tabs.map((tab) => {
          const active = isActive(tab.href);
          return (
            <Link
              key={tab.label}
              href={tab.href}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                active
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>
      <button
        onClick={handleLogout}
        disabled={isLoggingOut}
        className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:opacity-50"
      >
        {isLoggingOut ? 'Logging out…' : 'Logout'}
      </button>
    </div>
  );
}
