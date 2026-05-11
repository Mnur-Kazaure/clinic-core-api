// /projects/clinic-monorepo/clinic-app/src/api/client.ts
import axios from 'axios';

const LOCAL_API_FALLBACK = 'http://127.0.0.1:8110/api';

const isLoopbackHost = (host: string): boolean =>
  host === 'localhost' || host.startsWith('127.');

const resolveApiBaseUrl = (): string => {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();

  if (typeof window === 'undefined') {
    return configured || LOCAL_API_FALLBACK;
  }

  if (!configured) {
    return `${window.location.protocol}//${window.location.hostname}:8110/api`;
  }

  try {
    const configuredUrl = new URL(configured);
    const uiHost = window.location.hostname;

    // Keep loopback traffic same-site (localhost <-> 127.0.0.1) so auth cookies
    // are accepted/sent consistently, including private browsing sessions.
    if (
      isLoopbackHost(configuredUrl.hostname) &&
      isLoopbackHost(uiHost) &&
      configuredUrl.hostname !== uiHost
    ) {
      configuredUrl.hostname = uiHost;
      return configuredUrl.toString().replace(/\/$/, '');
    }
  } catch {
    return configured;
  }

  return configured;
};

const client = axios.create({
  baseURL: resolveApiBaseUrl(),
  withCredentials: true, // CRITICAL: Cookie-based auth
  headers: {
    'Content-Type': 'application/json',
  },
});

let activeDepartmentId: string | null = null;

export const setActiveDepartmentId = (departmentId: string | null) => {
  activeDepartmentId = departmentId;
};

client.interceptors.request.use((config) => {
  if (activeDepartmentId) {
    config.headers = config.headers ?? {};
    config.headers['X-Department-ID'] = activeDepartmentId;
  }
  return config;
});

// Response interceptor for auth errors
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired - handled by authService
      console.warn('Authentication required');
    }
    return Promise.reject(error);
  }
);

export default client;
