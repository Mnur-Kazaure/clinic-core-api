// /projects/clinic-monorepo/clinic-app/src/domains/auth/guards/authGuard.ts
import { roleSessionService } from '../services/roleSessionService';
import { UserDTO } from '@/shared/types';

/**
 * Invariant — Identity Authority
 *
 * Frontend identity context is valid if and only if it is obtained from
 * roleSessionService.getCurrentUser(), which calls /auth/me.
 * Any alternative source of identity or role context is a violation.
 */
export async function authGuard(): Promise<{isAuthenticated: boolean; user?: UserDTO}> {
  try {
    const user = await roleSessionService.getCurrentUser();
    console.log('🔐 [authGuard] User fetched:', { id: user.id.substring(0, 8), role: user.role });
    return { isAuthenticated: user.is_active === true, user };
  } catch (error: any) {
    console.error('❌ [authGuard] Failed:', error.response?.status || error.message);
    return { isAuthenticated: false };
  }
}


// // /projects/clinic-monorepo/clinic-app/src/domains/auth/guards/authGuard.ts
// import { roleSessionService } from '../services/roleSessionService';

// /**
//  * Invariant — Identity Authority
//  *
//  * Frontend identity context is valid if and only if it is obtained from
//  * roleSessionService.getCurrentUser(), which calls /auth/me and depends on
//  * backend get_current_user. Any alternative source of identity or role
//  * context is a design violation.
//  */
// export async function authGuard(): Promise<boolean> {
//   try {
//     const user = await roleSessionService.getCurrentUser();
//     return user.is_active === true;
//   } catch (error) {
//     return false;
//   }
// }
