'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { authGuard } from '@/domains/auth/guards/authGuard';
import { roleContextGuard } from '@/domains/auth/guards/roleContextGuard';
import { UserDTO } from '@/shared/types';
import { DashboardUserProvider } from '@/app/components/DashboardUserContext';
import { clinicService } from '@/domains/clinic/services/clinicService';
import { authService } from '@/domains/auth/services/authService';
import { normalizeClinicDisplayName } from '@/shared/constants/branding';

export default function AccountantLayout({
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
  const [isLoggingOut, setIsLoggingOut] = useState(false);

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

        if (user.role !== 'ACCOUNTANT') {
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

  if (authStatus !== 'authorized') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Verifying accountant access...</p>
        </div>
      </div>
    );
  }

  const displayClinicName = normalizeClinicDisplayName(clinicName);

  return (
    <DashboardUserProvider user={user}>
      <div className="min-h-screen bg-slate-950">
        <header className="border-b border-slate-700/70 bg-slate-950 text-white shadow-[0_18px_50px_-30px_rgba(8,47,73,0.9)]">
          <div className="mx-auto max-w-[1600px] px-4 sm:px-6 lg:px-8">
            <div className="flex min-h-16 flex-col justify-center gap-3 py-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="min-w-0">
                <p className="text-[10px] font-black uppercase tracking-[0.18em] text-cyan-300">
                  KSH Enterprise HIS
                </p>
                <div className="mt-1 flex flex-wrap items-center gap-3">
                  <h1 className="text-base font-black tracking-tight text-white sm:text-lg">
                    {displayClinicName}
                  </h1>
                  <span className="whitespace-nowrap rounded-full border border-cyan-300/30 bg-cyan-400/10 px-2.5 py-1 text-[11px] font-black text-cyan-100">
                    Accountant Financial Control Center
                  </span>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-amber-300/30 bg-amber-400/10 px-3 py-1.5 text-xs font-black text-amber-100">
                  Daily Close: Pending
                </span>
                <span className="rounded-full border border-rose-300/30 bg-rose-400/10 px-3 py-1.5 text-xs font-black text-rose-100">
                  Variance Review: 3
                </span>
                <button
                  type="button"
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                  className="rounded-full border border-white/15 bg-white/10 px-4 py-1.5 text-xs font-black text-white transition hover:border-cyan-200/60 hover:bg-cyan-300/10 disabled:opacity-50"
                >
                  {isLoggingOut ? 'Logging out...' : 'Logout'}
                </button>
              </div>
            </div>
          </div>
        </header>
        <main className="p-3 sm:p-4 lg:p-5">{children}</main>
      </div>
    </DashboardUserProvider>
  );
}
