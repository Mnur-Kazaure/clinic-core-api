// clinic-app/src/shared/constants/roleRoutes.ts
// Single source of truth for role -> dashboard route mapping.
export const roleRoutes = {
  RECEPTION: '/reception',
  DOCTOR: '/doctor',
  LAB: '/lab',
  PHARMACY: '/pharmacy',
  // ANC clinic owner (Community Health Extension Worker)
  CHEW: '/anc',
  // Maternity / labour & delivery owner
  MIDWIFE: '/maternity',
  ADMIN: '/admin',
  CLINIC_ADMIN: '/admin',
} as const;

