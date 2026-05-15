// /projects/clinic-monorepo/clinic-app/src/domains/clinic/services/clinicService.ts
import client from '@/api/client';
import { UserRole } from '@/shared/enums';
import { ClinicProfileResponse, ClinicRegistrationFeeResponse, StaffResponse } from '@/shared/types';

export interface ClinicProfileUpdateRequest {
  name?: string;
  logo_url?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  timezone?: string | null;
  registration_fee_minor?: number | null;
  registration_fee_required?: boolean;
  monthly_revenue_target_minor?: number | null;
  description?: string | null;
}

export interface StaffCreateRequest {
  full_name: string;
  email: string;
  password: string;
  role: UserRole;
  allowed_lab_unit_ids?: string[];
  default_lab_unit_id?: string | null;
}

export interface StaffUpdateRequest {
  full_name?: string | null;
  role?: UserRole;
  is_active?: boolean;
  specialty?: string | null;
  department?: string | null;
  room_label?: string | null;
  availability_status?: string | null;
  allowed_lab_unit_ids?: string[];
  default_lab_unit_id?: string | null;
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

  async getRegistrationFee(): Promise<ClinicRegistrationFeeResponse> {
    const response = await client.get('/v1/clinic/registration-fee');
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
