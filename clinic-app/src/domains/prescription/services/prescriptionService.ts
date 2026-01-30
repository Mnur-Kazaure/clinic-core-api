import client from '@/api/client';

export interface PrescriptionCreateRequest {
  consultation_id: string;
  drug_name: string;
  dosage: string;
  frequency: string;
  duration: string;
  instructions?: string;
}

export interface PrescriptionResponse {
  id: string;
  consultation_id: string;
  visit_id: string;
  drug_name: string;
  dosage: string;
  frequency: string;
  duration: string;
  instructions: string | null;
  status: 'ISSUED' | 'DISPENSED' | 'CANCELLED';
  prescribed_by: string;
  dispensed_by: string | null;
  issued_at: string;
  dispensed_at: string | null;
  cancelled_at: string | null;
}

export const prescriptionService = {
  async issuePrescription(
    payload: PrescriptionCreateRequest
  ): Promise<PrescriptionResponse> {
    const response = await client.post('/v1/prescriptions', payload);
    return response.data;
  },
};
