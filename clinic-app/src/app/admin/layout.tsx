// clinic-app/src/app/admin/layout.tsx
'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { authGuard } from '@/domains/auth/guards/authGuard';
import { roleContextGuard } from '@/domains/auth/guards/roleContextGuard';
import { AdminSidebar } from './components/AdminSidebar';
import { AdminTopNav } from './components/AdminTopNav';
import { clinicService } from '@/domains/clinic/services/clinicService';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [authStatus, setAuthStatus] = useState<
    'checking' | 'authorized' | 'unauthorized'
  >('checking');
  const [clinicName, setClinicName] = useState<string | null>(null);

  useEffect(() => {
    async function verifyAccess() {
      try {
        const { isAuthenticated, user } = await authGuard();

        if (!isAuthenticated || !user) {
          router.push('/login');
          return;
        }

        const redirectPath = roleContextGuard(user.role, pathname);

        if (redirectPath) {
          router.push(redirectPath);
          return;
        }

        if (user.role !== 'CLINIC_ADMIN') {
          router.push('/confirm-access');
          return;
        }

        try {
          const profile = await clinicService.getProfile();
          setClinicName(profile.name);
        } catch {
          setClinicName(null);
        }
        setAuthStatus('authorized');
      } catch {
        router.push('/confirm-access');
        setAuthStatus('unauthorized');
      }
    }

    verifyAccess();
  }, [router, pathname]);

  if (authStatus !== 'authorized') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">
            Verifying clinic admin access...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 admin-font">
      <div className="border-b border-slate-200 bg-slate-900 text-slate-100">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-2 text-xs">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400"></span>
            <span className="font-medium">System operational</span>
            <span className="text-slate-400">|</span>
            <span className="font-mono">
              {clinicName || 'Clinic Admin'}
            </span>
          </div>
          <div className="flex items-center gap-3 text-slate-300">
            <span className="font-mono">
              {new Date().toLocaleDateString('en-GB', {
                weekday: 'short',
                day: '2-digit',
                month: 'short',
                year: 'numeric',
              })}
            </span>
            <span className="text-slate-500">|</span>
            <span className="font-mono">
              {new Date().toLocaleTimeString('en-GB', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>
        </div>
      </div>

      <div className="flex min-h-[calc(100vh-40px)]">
        <aside className="hidden w-64 border-r border-slate-200 bg-white lg:block">
          <AdminSidebar clinicName={clinicName || 'Clinic Admin'} />
        </aside>
        <div className="flex-1">
          <div className="border-b border-slate-200 bg-white">
            <AdminTopNav />
          </div>
          <main className="mx-auto max-w-7xl px-6 py-8 space-y-6">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
