// /projects/clinic-monorepo/clinic-app/src/app/reception/layout.tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { authGuard } from '@/domains/auth/guards/authGuard';
import { roleContextGuard } from '@/domains/auth/guards/roleContextGuard';
import { UserDTO } from '@/shared/types';
import { Header } from '../components/Header';
import { clinicService } from '@/domains/clinic/services/clinicService';

export default function ReceptionLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [authStatus, setAuthStatus] = useState<'checking' | 'authorized' | 'unauthorized'>('checking');
  const [user, setUser] = useState<UserDTO | null>(null);
  const [clinicName, setClinicName] = useState<string | null>(null);

  useEffect(() => {
    async function verifyAccess() {
      try {
        // 1. Authentication guard (returns user if authenticated)
        const { isAuthenticated, user } = await authGuard();
        
        if (!isAuthenticated || !user) {
          router.push('/login');
          return;
        }

        // 2. Role context guard
        const redirectPath = roleContextGuard(user.role, pathname);
        
        if (redirectPath) {
          router.push(redirectPath);
          return;
        }

        // 3. Ensure user is actually RECEPTION
        if (user.role !== 'RECEPTION') {
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
      } catch (error: any) {
        console.error('❌ [ReceptionLayout] Access verification failed:', error);
        router.push('/confirm-access');
        setAuthStatus('unauthorized');
      }
    }

    verifyAccess();
  }, [router, pathname]);

  // Show loading while verifying
  if (authStatus !== 'authorized') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Verifying reception access...</p>
        </div>
      </div>
    );
  }

  // ✅ Pass user data down via props to children
  return (
    <div className="min-h-screen bg-gray-50">
      {user && (
        <Header
          userRole={user.role}
          userName={user.full_name}
          clinicName={clinicName}
        />
      )}
      <main className="p-6">
        {/* Pass user as props to children via React.cloneElement */}
        {children}
      </main>
    </div>
  );
}





// // /projects/clinic-monorepo/clinic-app/src/app/reception/layout.tsx
// 'use client';

// import { useEffect, useState } from 'react';
// import { useRouter, usePathname } from 'next/navigation';
// import { authGuard } from '@/domains/auth/guards/authGuard';
// import { roleContextGuard } from '@/domains/auth/guards/roleContextGuard';
// import { roleSessionService } from '@/domains/auth/services/roleSessionService';

// export default function ReceptionLayout({
//   children,
// }: {
//   children: React.ReactNode;
// }) {
//   const router = useRouter();
//   const pathname = usePathname();
//   const [isAuthorized, setIsAuthorized] = useState(false);

//   useEffect(() => {
//     async function verifyAccess() {
//       try {
//         // 1. Authentication guard
//         const isAuthenticated = await authGuard();
//         if (!isAuthenticated) {
//           router.push('/login');
//           return;
//         }

//         // 2. Get user for role check
//         const user = await roleSessionService.getCurrentUser();
        
//         // 3. Role context guard
//         const redirectPath = roleContextGuard(user.role, pathname);
//         if (redirectPath) {
//           router.push(redirectPath);
//           return;
//         }

//         // 4. Ensure user is actually RECEPTION
//         if (user.role !== 'RECEPTION') {
//           router.push('/confirm-access');
//           return;
//         }

//         setIsAuthorized(true);
//       } catch (error) {
//         router.push('/login');
//       }
//     }

//     verifyAccess();
//   }, [router, pathname]);

//   // Show loading while verifying
//   if (!isAuthorized) {
//     return (
//       <div className="min-h-screen flex items-center justify-center">
//         <div className="text-center">
//           <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
//           <p className="mt-2 text-gray-600">Verifying access...</p>
//         </div>
//       </div>
//     );
//   }

//   return <>{children}</>;
// }
