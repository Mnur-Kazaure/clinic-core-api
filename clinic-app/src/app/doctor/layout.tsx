// /projects/clinic-monorepo/clinic-app/src/app/doctor/layout.tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { authGuard } from '@/domains/auth/guards/authGuard';
import { roleContextGuard } from '@/domains/auth/guards/roleContextGuard';
import { UserDTO } from '@/shared/types';
import { Header } from '../components/Header';
import { DashboardUserProvider } from '@/app/components/DashboardUserContext';
import { clinicService } from '@/domains/clinic/services/clinicService';

export default function DoctorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
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

        if (user.role !== 'DOCTOR') {
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
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Verifying doctor access...</p>
        </div>
      </div>
    );
  }

  return (
    <DashboardUserProvider user={user}>
      <div className="min-h-screen bg-gray-50">
        {user && <Header userRole={user.role} clinicName={clinicName} />}
        {children}
      </div>
    </DashboardUserProvider>
  );
}
