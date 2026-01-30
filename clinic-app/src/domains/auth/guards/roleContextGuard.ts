// /projects/clinic-monorepo/clinic-app/src/domains/auth/guards/roleContextGuard.ts
import { roleRoutes } from '@/shared/constants/roleRoutes';

/**
 * Role Context Guard
 *
 * Enforces that role-based routing ALWAYS passes through /select-role.
 * Direct dashboard routing on mismatch is forbidden.
 */
export function roleContextGuard(
  userRole: string,
  currentPath: string
): string | null {
  const expectedRoute = roleRoutes[userRole as keyof typeof roleRoutes];

  // Invalid or unsupported role → mandatory gate
  if (!expectedRoute) {
    return '/confirm-access';
  }

  // Path does not match role namespace → mandatory gate
  if (!currentPath.startsWith(expectedRoute)) {
    return '/confirm-access';
  }

  // Guard passed
  return null;
}
///////////////////////////////////////////
