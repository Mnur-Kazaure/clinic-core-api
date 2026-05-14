// clinic-app/src/app/cmd/layout.tsx
'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { authGuard } from '@/domains/auth/guards/authGuard';
import { roleContextGuard } from '@/domains/auth/guards/roleContextGuard';
import { CmdSidebar } from './components/CmdSidebar';
import { AdminTopNav } from '../admin/components/AdminTopNav';
import { clinicService } from '@/domains/clinic/services/clinicService';

export default function CmdLayout({
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

        if (user.role !== 'CMD') {
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
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">
            Verifying Chief Medical Director authority...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] admin-font flex">
      {/* Sidebar */}
      <aside className="hidden w-72 border-r border-slate-200 bg-white lg:block sticky top-0 h-screen overflow-y-auto z-20">
        <CmdSidebar clinicName={clinicName || 'Clinic CMD'} />
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Status Bar - High Visibility */}
        <div className="border-b border-slate-800 bg-[#0F172A] text-slate-100 sticky top-0 z-30 shadow-sm">
          <div className="mx-auto flex w-full items-center justify-between px-6 py-2.5 text-[10px]">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="font-bold tracking-widest text-emerald-400 uppercase">System Status: Optimal</span>
              </div>
              <span className="text-slate-600 font-light">|</span>
              <div className="flex items-center gap-2">
                <span className="text-slate-400 uppercase tracking-wider font-semibold">Terminal ID:</span>
                <span className="font-mono text-indigo-300">CMD-SEC-7742</span>
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <span className="text-slate-400 uppercase tracking-wider font-semibold">Role:</span>
                <span className="bg-indigo-600 px-2 py-0.5 rounded text-[9px] font-bold">CHIEF MEDICAL DIRECTOR</span>
              </div>
              <div className="h-4 w-[1px] bg-slate-700"></div>
              <div className="flex items-center gap-3 font-mono text-slate-300">
                <span className="tracking-tighter uppercase">
                  {new Date().toLocaleDateString('en-GB', {
                    weekday: 'short',
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric',
                  })}
                </span>
                <span className="text-slate-600">/</span>
                <span className="font-bold">
                  {new Date().toLocaleTimeString('en-GB', {
                    hour12: false,
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  })}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Global Nav */}
        <header className="border-b border-slate-200 bg-white/80 backdrop-blur-md sticky top-[37px] z-20">
          <AdminTopNav />
        </header>

        {/* Dynamic Page Content */}
        <main className="flex-1 p-8 max-w-[1600px] mx-auto w-full">
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
            {children}
          </div>
        </main>
        
        {/* Footer Audit Signature */}
        <footer className="px-8 py-4 border-t border-slate-100 bg-slate-50 text-[10px] text-slate-400 flex justify-between items-center">
          <div className="flex gap-4">
            <span>&copy; 2026 KSH EMR/HIS — COMMAND MODULE V3.0</span>
            <span className="text-slate-300">|</span>
            <span>SECURE AES-256 ENCRYPTION ACTIVE</span>
          </div>
          <div className="font-mono uppercase tracking-tighter">
            Audit Hash: 8f2a...9c3e
          </div>
        </footer>
      </div>
    </div>
  );
}
