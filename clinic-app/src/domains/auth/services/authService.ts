// /projects/clinic-monorepo/clinic-app/src/domains/auth/services/authService.ts
import client from '@/api/client';

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

export const authService = {
  async login(credentials: LoginCredentials): Promise<void> {
    try {
      await client.post('/v1/auth/login', credentials);
    } catch (error: any) {
      if (error.response?.status === 401) {
        throw new AuthError('Invalid email or password');
      }
      if (error.response?.status === 403) {
        throw new AuthError('Account inactive or access denied');
      }
      throw new AuthError('Login failed. Please try again.');
    }
  },

  async logout(): Promise<void> {
    try {
      await client.post('/v1/auth/logout');
    } catch (error) {
      // Silent fail on logout - clear client-side anyway
      console.warn('Logout API call failed');
    }
  },

  // Optional for future use
  async refreshToken(): Promise<void> {
    try {
      await client.post('/v1/auth/refresh');
    } catch (error) {
      throw new AuthError('Session expired. Please login again.');
    }
  },
};