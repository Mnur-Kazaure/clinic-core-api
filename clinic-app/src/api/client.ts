// /projects/clinic-monorepo/clinic-app/src/api/client.ts
import axios from 'axios';

const client = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
  withCredentials: true, // CRITICAL: Cookie-based auth
  headers: {
    'Content-Type': 'application/json',
  },
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
