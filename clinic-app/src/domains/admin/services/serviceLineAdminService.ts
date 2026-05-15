import client from '@/api/client';
import { ServiceLineKind } from '@/shared/enums';

export interface DepartmentDTO {
  id: string;
  clinic_id: string;
  name: string;
}

export interface ServiceLineTreeNodeDTO {
  id: string;
  clinic_id: string;
  name: string;
  parent_id: string | null;
  department_id: string | null;
  default_child_id: string | null;
  requires_doctor: boolean;
  service_line_kind: ServiceLineKind;
  is_active: boolean;
  children: ServiceLineTreeNodeDTO[];
}

export interface ServiceLineDTO {
  id: string;
  clinic_id: string;
  name: string;
  parent_id: string | null;
  department_id: string | null;
  default_child_id: string | null;
  requires_doctor: boolean;
  service_line_kind: ServiceLineKind;
  is_active: boolean;
}

export interface ServiceLineCreatePayload {
  name: string;
  parent_id?: string | null;
  department_id?: string | null;
  default_child_id?: string | null;
  requires_doctor?: boolean;
  service_line_kind?: ServiceLineKind;
  is_active?: boolean;
}

export interface ServiceLineUpdatePayload {
  name?: string;
  parent_id?: string | null;
  department_id?: string | null;
  default_child_id?: string | null;
  requires_doctor?: boolean;
  service_line_kind?: ServiceLineKind;
  is_active?: boolean;
}

export interface UserDepartmentMappingDTO {
  id: string;
  user_id: string;
  department_id: string;
  is_primary: boolean;
}

export interface DoctorServiceLineMappingDTO {
  id: string;
  doctor_id: string;
  service_line_id: string;
}

export const serviceLineAdminService = {
  async listDepartments(): Promise<DepartmentDTO[]> {
    const response = await client.get('/v1/departments');
    return response.data;
  },

  async listServiceLines(params?: {
    include_inactive?: boolean;
    department_id?: string;
    service_line_kind?: ServiceLineKind;
  }): Promise<ServiceLineTreeNodeDTO[]> {
    const response = await client.get('/v1/service-lines', { params });
    return response.data;
  },

  async createServiceLine(
    payload: ServiceLineCreatePayload
  ): Promise<ServiceLineDTO> {
    const response = await client.post('/v1/service-lines', payload);
    return response.data;
  },

  async updateServiceLine(
    serviceLineId: string,
    payload: ServiceLineUpdatePayload
  ): Promise<ServiceLineDTO> {
    const response = await client.put(`/v1/service-lines/${serviceLineId}`, payload);
    return response.data;
  },

  async deactivateServiceLine(serviceLineId: string): Promise<void> {
    await client.delete(`/v1/service-lines/${serviceLineId}`);
  },

  async listUserDepartments(userId: string): Promise<UserDepartmentMappingDTO[]> {
    const response = await client.get(`/v1/users/${userId}/departments`);
    return response.data;
  },

  async assignUserDepartment(
    userId: string,
    payload: { department_id: string; is_primary?: boolean }
  ): Promise<UserDepartmentMappingDTO> {
    const response = await client.post(`/v1/users/${userId}/departments`, payload);
    return response.data;
  },

  async removeUserDepartment(userId: string, departmentId: string): Promise<void> {
    await client.delete(`/v1/users/${userId}/departments/${departmentId}`);
  },

  async listDoctorServiceLines(
    doctorId: string
  ): Promise<DoctorServiceLineMappingDTO[]> {
    const response = await client.get(`/v1/doctors/${doctorId}/service-lines`);
    return response.data;
  },

  async assignDoctorServiceLine(
    doctorId: string,
    payload: { service_line_id: string }
  ): Promise<DoctorServiceLineMappingDTO> {
    const response = await client.post(`/v1/doctors/${doctorId}/service-lines`, payload);
    return response.data;
  },

  async removeDoctorServiceLine(
    doctorId: string,
    serviceLineId: string
  ): Promise<void> {
    await client.delete(`/v1/doctors/${doctorId}/service-lines/${serviceLineId}`);
  },
};
