// 1. shared/constants/roleRoutes.ts
export const roleRoutes = {
  RECEPTION: '/reception',
  DOCTOR: '/doctor',
  LAB: '/lab',
  PHARMACY: '/pharmacy',
  ADMIN: '/admin',
  CLINIC_ADMIN: '/admin',
} as const;

// 2. shared/enums.ts
export enum UserRole {
  RECEPTION = 'RECEPTION',
  DOCTOR = 'DOCTOR',
  LAB = 'LAB',
  PHARMACY = 'PHARMACY',
  ADMIN = 'ADMIN',
  CLINIC_ADMIN = 'CLINIC_ADMIN',
  SYSTEM = 'SYSTEM', // For backend only
}

// 3. api/client.ts (update existing)
// Ensure it has cookie-based auth setup