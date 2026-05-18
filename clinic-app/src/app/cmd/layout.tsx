'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { DashboardUserProvider } from '@/app/components/DashboardUserContext';
import { authGuard } from '@/domains/auth/guards/authGuard';
import { roleContextGuard } from '@/domains/auth/guards/roleContextGuard';
import { UserDTO } from '@/shared/types';

const CMD_DASHBOARD_ROLES = new Set(['CMD']);

export default function CmdLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [authStatus, setAuthStatus] = useState<'checking' | 'authorized' | 'unauthorized'>('checking');
  const [user, setUser] = useState<UserDTO | null>(null);

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
      <div className="flex min-h-screen items-center justify-center bg-[#06111f] text-white">
        <div className="rounded-lg border border-cyan-300/20 bg-white/[0.06] px-8 py-7 text-center shadow-2xl shadow-cyan-950/30">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-cyan-300" />
          <p className="mt-4 text-sm font-semibold text-cyan-50">Verifying CMD access...</p>
          <p className="mt-2 text-xs text-slate-400">Executive command center authorization</p>
        </div>
      </div>
    );
  }

  return (
    <DashboardUserProvider user={user}>
      {children}
    </DashboardUserProvider>
  );
}
