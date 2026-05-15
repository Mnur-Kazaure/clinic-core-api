// /projects/clinic-monorepo/clinic-app/src/components/Header.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authService } from '@/domains/auth/services/authService';
import { LAB_WORKSPACE_THEME } from '@/domains/lab/constants/labWorkspaceTheme';
import { normalizeClinicDisplayName } from '@/shared/constants/branding';

interface HeaderProps {
  userRole: string;
  clinicName?: string | null;
  variant?: 'default' | 'lab';
}

export function Header({ userRole, clinicName, variant = 'default' }: HeaderProps) {
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const displayClinicName = normalizeClinicDisplayName(clinicName);
  const isLabVariant = variant === 'lab';

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

  const roleLabels: Record<string, string> = {
    RECEPTION: 'Reception',
    CASHIER: 'Cashier',
    ACCOUNTANT: 'Accountant',
    CMD: 'Chief Medical Director (CMD)',
    DOCTOR: 'Doctor',
    LAB: 'Lab Technician',
    LAB_TECH: 'Lab Technician',
    LAB_SCIENTIST: 'Laboratory Scientist',
    LAB_SUPERVISOR: 'Laboratory Supervisor',
    LAB_MANAGER: 'Medical Laboratory HOD',
    PHARMACY: 'Pharmacist',
    PHARMACY_HOD: 'Pharmacy HOD',
    PHARMACY_STORE_OFFICER: 'Pharmacy Store Officer',
    ADMIN: 'Administrator',
    CLINIC_ADMIN: 'Clinic Admin',
  };

  return (
    <header
      data-testid="app-header-shell"
      className={isLabVariant ? 'border-b' : 'bg-white shadow border-b'}
      style={
        isLabVariant
          ? {
              background: LAB_WORKSPACE_THEME.shellBackground,
              borderBottomColor: LAB_WORKSPACE_THEME.border,
              boxShadow: LAB_WORKSPACE_THEME.shellShadow,
            }
          : undefined
      }
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <h1
              className={`text-xl font-bold ${isLabVariant ? '' : 'text-gray-900'}`}
              style={isLabVariant ? { color: LAB_WORKSPACE_THEME.textPrimary } : undefined}
            >
              {displayClinicName}
            </h1>
            <div
              data-testid="app-header-role-badge"
              className={`ml-4 rounded-full px-3 py-1 text-sm font-medium ${
                isLabVariant ? 'border' : 'bg-blue-100 text-blue-800'
              }`}
              style={
                isLabVariant
                  ? {
                      background: LAB_WORKSPACE_THEME.badgeBackground,
                      color: LAB_WORKSPACE_THEME.badgeText,
                      borderColor: LAB_WORKSPACE_THEME.badgeBorder,
                    }
                  : undefined
              }
            >
              {roleLabels[userRole] || userRole}
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <button
              onClick={handleLogout}
              disabled={isLoggingOut}
              className={`rounded-md px-4 py-2 text-sm font-medium disabled:opacity-50 ${
                isLabVariant
                  ? 'text-[#1E4B8C] hover:bg-[#F5FAFE] hover:text-[#0F172A]'
                  : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
              }`}
            >
              {isLoggingOut ? 'Logging out...' : 'Logout'}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
