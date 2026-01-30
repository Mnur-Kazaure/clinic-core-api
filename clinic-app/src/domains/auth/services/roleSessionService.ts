// /projects/clinic-monorepo/clinic-app/src/domains/auth/services/roleSessionService.ts
import client from '@/api/client';
import { UserDTO } from '@/shared/types';

export const roleSessionService = {
  /**
   * Invariant — Identity Authority
   *
   * Frontend identity context is valid if and only if it is obtained from
   * this method, which calls GET /v1/auth/me (backend get_current_user).
   *
   * Forbidden:
   * - JWT decoding
   * - localStorage/sessionStorage
   * - caching identity
   * - alternative identity sources (even as comments)
   */
  async getCurrentUser(): Promise<UserDTO> {
    const response = await client.get('/v1/auth/me');

    const user = response.data;

    if (!user?.id || !user?.role || !user?.clinic_id) {
      throw new Error('Invalid user data received from server');
    }

    return user;
  },
};
