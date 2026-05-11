// /projects/clinic-monorepo/clinic-app/src/domains/auth/services/authService.ts
import client from '@/api/client';
import { setActiveDepartmentId } from '@/api/client';

export interface LoginCredentials {
  email: string;
  password: string;
}

export class AuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AuthError';
  }
}

const getResponseStatus = (error: unknown) => {
  if (!error || typeof error !== 'object' || !('response' in error)) {
    return null;
  }
  const status = (error as { response?: { status?: number } }).response?.status;
  return typeof status === 'number' ? status : null;
};

export const authService = {
  async login(credentials: LoginCredentials): Promise<void> {
    try {
      await client.post('/v1/auth/login', credentials);
      setActiveDepartmentId(null);
    } catch (error: unknown) {
      const status = getResponseStatus(error);
      if (status === 401) {
        throw new AuthError('Invalid email or password');
      }
      if (status === 403) {
        throw new AuthError('Account inactive or access denied');
      }
      throw new AuthError('Login failed. Please try again.');
    }
  },

  async logout(): Promise<void> {
    try {
      await client.post('/v1/auth/logout');
    } catch {
      // Silent fail on logout - clear client-side anyway
      console.warn('Logout API call failed');
    } finally {
      setActiveDepartmentId(null);
    }
  },

  // Optional for future use
  async refreshToken(): Promise<void> {
    try {
      await client.post('/v1/auth/refresh');
    } catch {
      throw new AuthError('Session expired. Please login again.');
    }
  },

  async switchDepartment(
    departmentId: string
  ): Promise<{
    detail: string;
    current_department_id: string;
    allowed_department_ids: string[];
  }> {
    const response = await client.post('/v1/auth/switch-department', {
      department_id: departmentId,
    });
    const payload = response.data;
    if (payload?.current_department_id) {
      setActiveDepartmentId(payload.current_department_id);
    }
    return payload;
  },
};
