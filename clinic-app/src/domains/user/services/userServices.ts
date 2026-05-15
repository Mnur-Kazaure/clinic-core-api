// /projects/clinic-monorepo/clinic-app/src/domains/user/services/userService.ts
import client from '@/api/client';

export interface Doctor {
  id: string;
  full_name: string | null;
  email: string;
  role?: string;
  specialty?: string | null;
  department?: string | null;
  room_label?: string | null;
  availability_status?: string | null;
}

export const userService = {
  // List doctors in clinic
  async listDoctors(): Promise<Doctor[]> {
    const response = await client.get('/v1/users/doctors');
    return response.data;
  },

  async listChews(): Promise<Doctor[]> {
    const response = await client.get('/v1/users/chews');
    return response.data;
  },

  async listMidwives(): Promise<Doctor[]> {
    const response = await client.get('/v1/users/midwives');
    return response.data;
  },

  async listAssignableStaff(params?: {
    service_line_id?: string;
    role?: string;
    include_all_departments?: boolean;
    department_id?: string | null;
  }): Promise<Doctor[]> {
    const response = await client.get('/v1/users/assignable', { params });
    return response.data;
  },
};
