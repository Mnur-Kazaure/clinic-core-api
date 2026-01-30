// /projects/clinic-monorepo/clinic-app/src/domains/patient/services/patientService.ts
import client from '@/api/client';
import { PatientResponse } from './types';

export interface PatientCreateRequest {
  full_name: string;
  date_of_birth: string; // "YYYY-MM-DD"
  gender: 'MALE' | 'FEMALE';
  phone_number: string;
  address: string;
  occupation: string;
}

export const patientService = {
  // Create new patient
  async createPatient(payload: PatientCreateRequest): Promise<PatientResponse> {
    const response = await client.post('/v1/patient', payload);
    return response.data;
  },

  // Search patients
  async searchPatients(params: {
    q?: string;
    full_name?: string;
    phone_number?: string;
    limit?: number;
  }): Promise<PatientResponse[]> {
    const response = await client.get('/v1/patient/search', { params });
    return response.data;
  },
};