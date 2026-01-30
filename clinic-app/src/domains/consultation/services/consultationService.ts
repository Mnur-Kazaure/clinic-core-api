import client from '@/api/client';
import { ConsultationResponse } from '@/shared/types';
import { jsonUtils } from '@/shared/utils/json';

export interface ConsultationCreateRequest {
  visit_id: string;
}

export interface ConsultationUpdateRequest {
  vitals?: string | null;
  presenting_complaints?: string | null;
  diagnosis?: string | null;
  notes?: string | null;
  doctor_full_name?: string | null;
}

export interface ConsultationFormData {
  vitals?: Record<string, any>;
  presenting_complaints?: string;
  diagnosis?: string;
  notes?: string;
  doctor_full_name?: string;
}

export const consultationService = {
  async startConsultation(visitId: string): Promise<ConsultationResponse> {
    const response = await client.post('/v1/consultations/start', {
      visit_id: visitId,
    });
    return response.data;
  },

  async getConsultationByVisit(
    visitId: string
  ): Promise<ConsultationResponse | null> {
    try {
      const response = await client.get(`/v1/consultations/visit/${visitId}`);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },

  async updateConsultation(
    consultationId: string,
    data: ConsultationUpdateRequest
  ): Promise<ConsultationResponse> {
    const response = await client.patch(
      `/v1/consultations/${consultationId}`,
      data
    );
    return response.data;
  },

  async completeConsultation(
    consultationId: string
  ): Promise<ConsultationResponse> {
    const response = await client.post(
      `/v1/consultations/${consultationId}/complete`,
      {}
    );
    return response.data;
  },

  prepareUpdateData(formData: ConsultationFormData): ConsultationUpdateRequest {
    return {
      vitals: jsonUtils.stringifyVitals(formData.vitals || null),
      presenting_complaints: formData.presenting_complaints || null,
      diagnosis: formData.diagnosis || null,
      notes: formData.notes || null,
      doctor_full_name: formData.doctor_full_name || null,
    };
  },
};
