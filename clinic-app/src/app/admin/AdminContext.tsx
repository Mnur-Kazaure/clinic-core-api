'use client';

import { createContext, useContext } from 'react';

export type AdminContextValue = {
  clinicName?: string | null;
};

const AdminContext = createContext<AdminContextValue>({});

export function AdminContextProvider({
  value,
  children,
}: {
  value: AdminContextValue;
  children: React.ReactNode;
}) {
  return <AdminContext.Provider value={value}>{children}</AdminContext.Provider>;
}

export function useAdminContext() {
  return useContext(AdminContext);
}
