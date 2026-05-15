'use client';

import { createContext, useContext } from 'react';
import { UserDTO } from '@/shared/types';

const DashboardUserContext = createContext<UserDTO | null>(null);

export function DashboardUserProvider({
  user,
  children,
}: {
  user: UserDTO | null;
  children: React.ReactNode;
}) {
  return (
    <DashboardUserContext.Provider value={user}>
      {children}
    </DashboardUserContext.Provider>
  );
}

export function useDashboardUser(): UserDTO | null {
  return useContext(DashboardUserContext);
}

export function getDashboardUserDisplayName(user: UserDTO | null): string {
  if (!user) return 'Unknown User';
  const fullName = user.full_name?.trim();
  if (fullName) return fullName;
  return user.email;
}
