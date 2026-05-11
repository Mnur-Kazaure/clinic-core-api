'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Header } from '@/app/components/Header';
import { DashboardUserProvider } from '@/app/components/DashboardUserContext';
import { authGuard } from '@/domains/auth/guards/authGuard';
import { roleContextGuard } from '@/domains/auth/guards/roleContextGuard';
import { clinicService } from '@/domains/clinic/services/clinicService';
import { UserDTO } from '@/shared/types';

const CMD_DASHBOARD_ROLES = new Set(['CMD']);

export default function CmdLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [authStatus, setAuthStatus] = useState<'checking' | 'authorized' | 'unauthorized'>('checking');
  const [user, setUser] = useState<UserDTO | null>(null);
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

        if (!CMD_DASHBOARD_ROLES.has(user.role)) {
          router.push('/confirm-access');
          return;
        }

        setUser(user);
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

    void verifyAccess();
  }, [pathname, router]);

  if (authStatus !== 'authorized') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600" />
          <p className="mt-2 text-gray-600">Verifying CMD access...</p>
        </div>
      </div>
    );
  }

  return (
    <DashboardUserProvider user={user}>
      <div className="min-h-screen bg-slate-50">
        {user ? <Header userRole={user.role} clinicName={clinicName} /> : null}
        <main className="p-6">{children}</main>
      </div>
    </DashboardUserProvider>
  );
}
