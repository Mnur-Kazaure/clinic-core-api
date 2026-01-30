// /projects/clinic-monorepo/clinic-app/src/domains/clinic/services/clinicService.ts
import client from '@/api/client';
import { UserRole } from '@/shared/enums';
import { ClinicProfileResponse, StaffResponse } from '@/shared/types';

export interface ClinicProfileUpdateRequest {
  name?: string;
  logo_url?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  timezone?: string | null;
  description?: string | null;
}

export interface StaffCreateRequest {
  full_name: string;
  email: string;
  password: string;
  role: UserRole;
}

export interface StaffUpdateRequest {
  full_name?: string | null;
  is_active?: boolean;
  specialty?: string | null;
  department?: string | null;
  room_label?: string | null;
  availability_status?: string | null;
}

export const clinicService = {
  async getProfile(): Promise<ClinicProfileResponse> {
    const response = await client.get('/v1/clinic/profile');
    return response.data;
  },

  async updateProfile(
    payload: ClinicProfileUpdateRequest
  ): Promise<ClinicProfileResponse> {
    const response = await client.patch('/v1/clinic/profile', payload);
    return response.data;
  },

  async listStaff(): Promise<StaffResponse[]> {
    const response = await client.get('/v1/clinic/staff');
    return response.data;
  },

  async createStaff(payload: StaffCreateRequest) {
    const response = await client.post('/v1/clinic/staff', payload);
    return response.data;
  },

  async updateStaff(
    staffId: string,
    payload: StaffUpdateRequest
  ): Promise<StaffResponse> {
    const response = await client.patch(`/v1/clinic/staff/${staffId}`, payload);
    return response.data;
  },

  async deleteStaff(staffId: string): Promise<void> {
    await client.delete(`/v1/clinic/staff/${staffId}`);
  },
};
