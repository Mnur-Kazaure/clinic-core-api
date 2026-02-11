// /projects/clinic-monorepo/clinic-app/src/app/confirm-access/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { roleSessionService } from '@/domains/auth/services/roleSessionService';
import { roleRoutes } from '@/shared/constants/roleRoutes';
import { UserRole } from '@/shared/enums';

export default function ConfirmAccessPage() {
  const router = useRouter();
  const [status, setStatus] = useState<'loading' | 'error' | 'redirecting'>('loading');
  const [errorMessage, setErrorMessage] = useState('');
  const [debugInfo, setDebugInfo] = useState<string>('');
  const [destinationLabel, setDestinationLabel] = useState<string>('');

  useEffect(() => {
    async function confirmAccess() {
      try {
        setStatus('loading');
        setDebugInfo('📡 Starting /me request...');
        console.log('📡 [DEBUG] Starting /me request from confirm-access page');
        
        // 🎯 CRITICAL: Only source of truth
        const user = await roleSessionService.getCurrentUser();
        
        console.log('✅ [DEBUG] /me response received:', user);
        setDebugInfo(`✅ /me response received. Role: ${user.role}, Active: ${user.is_active}`);
        
        // Validate user is active
        if (!user.is_active) {
          console.log('❌ [DEBUG] User account inactive');
          setErrorMessage('Account is not active. Please contact administrator.');
          setStatus('error');
          return;
        }
        
        // Validate role is supported
        // const route = roleRoutes[user.role as keyof typeof roleRoutes];
        const route = roleRoutes[user.role as UserRole];
        if (!route) {
          console.log(`❌ [DEBUG] Unsupported role: ${user.role}`);
          setErrorMessage(`Role "${user.role}" is not supported.`);
          setStatus('error');
          return;
        }
        
        console.log(`✅ [DEBUG] Role ${user.role} supported. Redirecting to: ${route}`);
        const roleLabels: Record<UserRole, string> = {
          RECEPTION: 'Reception',
          DOCTOR: 'Doctor',
          LAB: 'Lab',
          PHARMACY: 'Pharmacy',
          CHEW: 'ANC (CHEW)',
          MIDWIFE: 'Maternity (Midwife)',
          ADMIN: 'Admin',
          CLINIC_ADMIN: 'Clinic Admin',
          SYSTEM: 'System',
        };
        setDestinationLabel(roleLabels[user.role as UserRole] || 'Workspace');
        setDebugInfo('Routing to role workspace');
        
        // 🚨 GOVERNANCE: Mandatory gate complete → route to role dashboard
        setStatus('redirecting');
        setTimeout(() => {
          router.push(route);
        }, 1000); // 1 second delay to see debug info
        
      } catch (error: any) {
        console.error('❌ [DEBUG] /me fetch failed:', error);
        console.error('❌ [DEBUG] Error response:', error.response?.data);
        console.error('❌ [DEBUG] Error status:', error.response?.status);
        console.error('❌ [DEBUG] Error headers:', error.response?.headers);
        
        setDebugInfo(`❌ Error: ${error.message || 'Unknown error'}`);
        
        if (error.response?.status === 401) {
          console.log('❌ [DEBUG] 401 Unauthorized - redirecting to login');
          setDebugInfo('🔄 Token expired, redirecting to login...');
          setTimeout(() => {
            router.push('/login');
          }, 1500);
          return;
        }
        
        if (error.response?.status === 0) {
          setErrorMessage('Cannot connect to server. Check if backend is running.');
          setDebugInfo('🌐 Network error - backend may be down');
        } else if (error.response?.status === 403) {
          setErrorMessage('Access forbidden. Please contact administrator.');
          setDebugInfo('🚫 403 Forbidden - check CORS/cookie settings');
        } else {
          setErrorMessage('Unable to verify access. Please try again.');
          setDebugInfo(`Server error: ${error.response?.status || 'Unknown'}`);
        }
        
        setStatus('error');
      }
    }
    
    confirmAccess();
    
    // Log current cookies (document.cookie won't show HttpOnly)
    console.log('🍪 [DEBUG] Document cookies:', document.cookie);
    console.log('📍 [DEBUG] Current URL:', window.location.href);
    
  }, [router]);

  // Loading state
  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Confirming Access
          </h1>
          <p className="text-gray-600 mb-4">
            Preparing your workspace...
          </p>
          <div className="mt-4 p-3 bg-blue-50 rounded text-left">
            <p className="text-sm text-blue-800 font-mono">{debugInfo || 'Initializing...'}</p>
            <p className="text-xs text-gray-500 mt-2">
              Checking /me endpoint for role information...
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (status === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full p-8 bg-white rounded-lg shadow">
          <div className="text-red-500 text-4xl mb-4 text-center">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2 text-center">
            Access Issue
          </h1>
          <p className="text-gray-600 mb-4 text-center">{errorMessage}</p>
          
          <div className="mt-6 p-4 bg-yellow-50 rounded border border-yellow-200">
            <h3 className="font-semibold text-yellow-800 mb-2">Debug Information:</h3>
            <p className="text-sm text-yellow-700 font-mono break-all">{debugInfo}</p>
            <p className="text-xs text-yellow-600 mt-2">
              Check browser Network tab for /me request details
            </p>
          </div>
          
          <div className="mt-6 flex flex-col gap-3">
            <button
              onClick={() => router.push('/login')}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Return to Login
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Redirecting state
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center max-w-md">
        <div className="animate-pulse mb-4">
          <div className="h-12 w-12 bg-green-100 rounded-full mx-auto mb-4 flex items-center justify-center">
            <span className="text-2xl">✓</span>
          </div>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Access Confirmed!
        </h1>
        <p className="text-gray-600 mb-4">
          Preparing your {destinationLabel || 'role'} workspace
        </p>
        <div className="mt-4 p-3 bg-green-50 rounded">
          <p className="text-sm text-green-800">
            Securing session and loading dashboard
          </p>
          <div className="mt-2 flex justify-center">
            <div className="animate-pulse h-1 w-24 bg-green-400 rounded"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
