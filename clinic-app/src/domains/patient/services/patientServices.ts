// /projects/clinic-monorepo/clinic-app/src/domains/patient/services/patientService.ts
import client from '@/api/client';
import { PurposeOfUse } from '@/shared/enums';
import { PatientResponse } from './types';

export interface PatientCreateRequest {
  full_name: string;
  date_of_birth: string; // "YYYY-MM-DD"
  gender: 'MALE' | 'FEMALE' | 'UNKNOWN';
  phone_number: string;
  address: string;
  occupation: string;
  identity_state?: 'PROVISIONAL' | 'VERIFIED';
  created_reason?: string;
  registration_payment_method?: 'CASH' | 'TRANSFER';
  registration_payment_reference?: string;
}

export interface PatientSearchParams {
  q?: string;
  full_name?: string;
  phone_number?: string;
  limit?: number;
  purpose_of_use?: PurposeOfUse;
  justification?: string;
}

export const patientService = {
  // Create new patient
  async createPatient(payload: PatientCreateRequest): Promise<PatientResponse> {
    const response = await client.post('/v1/patient', payload);
    return response.data;
  },

  // Search patients
  async searchPatients(params: PatientSearchParams): Promise<PatientResponse[]> {
    const { purpose_of_use, justification, ...searchParams } = params;
    const trimmedJustification = justification?.trim();
    const response = await client.get('/v1/patient/search', {
      params: {
        ...searchParams,
        purpose_of_use: purpose_of_use ?? PurposeOfUse.OPERATIONS,
        justification:
          trimmedJustification && trimmedJustification.length >= 2
            ? trimmedJustification
            : 'Reception patient search',
      },
    });
    return response.data;
  },
};
