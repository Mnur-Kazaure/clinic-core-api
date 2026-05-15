'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { authGuard } from '@/domains/auth/guards/authGuard';
import { roleContextGuard } from '@/domains/auth/guards/roleContextGuard';
import { UserDTO } from '@/shared/types';
import { Header } from '@/app/components/Header';
import { DashboardUserProvider } from '@/app/components/DashboardUserContext';
import { clinicService } from '@/domains/clinic/services/clinicService';
import { LAB_WORKSPACE_THEME } from '@/domains/lab/constants/labWorkspaceTheme';

const allowedLabRoles = new Set([
  'LAB',
  'LAB_TECH',
  'LAB_SCIENTIST',
  'LAB_SUPERVISOR',
  'LAB_MANAGER',
]);

export default function LabLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [authStatus, setAuthStatus] = useState<
    'checking' | 'authorized' | 'unauthorized'
  >('checking');
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

        if (!allowedLabRoles.has(user.role)) {
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

    verifyAccess();
  }, [router, pathname]);

  if (authStatus !== 'authorized') {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: LAB_WORKSPACE_THEME.appBackground }}
      >
        <div className="text-center">
          <div
            className="mx-auto h-8 w-8 animate-spin rounded-full border-b-2"
            style={{ borderBottomColor: LAB_WORKSPACE_THEME.primary }}
          />
          <p className="mt-2 text-gray-600">Verifying lab access...</p>
        </div>
      </div>
    );
  }

  return (
    <DashboardUserProvider user={user}>
      <div className="min-h-screen" style={{ background: LAB_WORKSPACE_THEME.appBackground }}>
        {user && <Header userRole={user.role} clinicName={clinicName} variant="lab" />}
        <main className="p-6">{children}</main>
      </div>
    </DashboardUserProvider>
  );
}
