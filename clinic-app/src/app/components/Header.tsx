// /projects/clinic-monorepo/clinic-app/src/components/Header.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authService } from '@/domains/auth/services/authService';

interface HeaderProps {
  userRole: string;
  userName?: string | null;
  clinicName?: string | null;
}

export function Header({ userRole, userName, clinicName }: HeaderProps) {
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

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
    DOCTOR: 'Doctor',
    LAB: 'Lab Technician',
    PHARMACY: 'Pharmacist',
    ADMIN: 'Administrator',
    CLINIC_ADMIN: 'Clinic Admin',
  };

  return (
    <header className="bg-white shadow border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <h1 className="text-xl font-bold text-gray-900">
              {clinicName || 'Clinic'}
            </h1>
            <div className="ml-4 px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
              {roleLabels[userRole] || userRole}
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            {userName && (
              <span className="text-gray-700">{userName}</span>
            )}
            <button
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-md disabled:opacity-50"
            >
              {isLoggingOut ? 'Logging out...' : 'Logout'}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
