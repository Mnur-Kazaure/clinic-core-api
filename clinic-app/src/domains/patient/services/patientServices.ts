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

export interface PatientListParams {
  q?: string;
  limit?: number;
  offset?: number;
  purpose_of_use?: PurposeOfUse;
  justification?: string;
}

export interface PatientListResponse {
  total: number;
  limit: number;
  offset: number;
  items: PatientResponse[];
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

  async listPatients(
    params: PatientListParams = {}
  ): Promise<PatientListResponse> {
    const {
      purpose_of_use,
      justification,
      q,
      limit = 50,
      offset = 0,
    } = params;
    const trimmedJustification = justification?.trim();
    const response = await client.get('/v1/patient', {
      params: {
        q,
        limit,
        offset,
        purpose_of_use: purpose_of_use ?? PurposeOfUse.OPERATIONS,
        justification:
          trimmedJustification && trimmedJustification.length >= 2
            ? trimmedJustification
            : 'Reception patient registry review',
      },
    });
    return response.data;
  },

  async getPatientById(
    patientId: string,
    params?: { purpose_of_use?: PurposeOfUse; justification?: string }
  ): Promise<PatientResponse> {
    const trimmedJustification = params?.justification?.trim();
    const response = await client.get(`/v1/patient/${patientId}`, {
      params: {
        purpose_of_use: params?.purpose_of_use ?? PurposeOfUse.OPERATIONS,
        justification:
          trimmedJustification && trimmedJustification.length >= 2
            ? trimmedJustification
            : 'Reception patient detail review',
      },
    });
    return response.data;
  },
};
