// clinic-app/src/shared/constants/roleRoutes.ts
// Single source of truth for role -> dashboard route mapping.
export const roleRoutes = {
  RECEPTION: '/reception',
  CASHIER: '/cashier',
  ACCOUNTANT: '/accountant',
  CMD: '/cmd',
  DOCTOR: '/doctor',
  LAB: '/lab',
  LAB_TECH: '/lab',
  LAB_SCIENTIST: '/lab',
  LAB_SUPERVISOR: '/lab',
  LAB_MANAGER: '/lab/manager',
  PHARMACY: '/pharmacy',
  PHARMACY_HOD: '/pharmacy-hod',
  PHARMACY_STORE_OFFICER: '/pharmacy-store',
  // ANC clinic owner (Community Health Extension Worker)
  CHEW: '/anc',
  // Maternity / labour & delivery owner
  MIDWIFE: '/maternity',
  ADMIN: '/admin',
  CLINIC_ADMIN: '/admin',
} as const;
