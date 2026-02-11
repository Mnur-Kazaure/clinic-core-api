import client from '@/api/client';
import { PrescriptionFulfillmentType, PrescriptionStatus } from '@/shared/enums';
import { PrescriptionResponse } from '@/shared/types';

export interface DispenseCreateRequest {
  pharmacist_id: string;
  quantity: number;
}

export interface DispenseResponse {
  id: string;
  prescription_id: string;
  pharmacist_id: string;
  quantity: number;
}

export interface ExternalFulfillCreateRequest {
  note: string;
}

export interface PrescriptionFulfillmentResponse {
  id: string;
  clinic_id: string;
  prescription_id: string;
  actor_id: string;
  fulfillment_type: PrescriptionFulfillmentType;
  quantity: number | null;
  note: string | null;
  occurred_at: string;
}

export const pharmacyService = {
  async getPrescriptions(
    status?: PrescriptionStatus
  ): Promise<PrescriptionResponse[]> {
    const params = status ? { status } : {};
    const response = await client.get('/v1/pharmacy/prescriptions', { params });
    return response.data;
  },

  async getPrescription(
    prescriptionId: string
  ): Promise<PrescriptionResponse> {
    const response = await client.get(
      `/v1/pharmacy/prescriptions/${prescriptionId}`
    );
    return response.data;
  },

  async dispensePrescription(
    prescriptionId: string,
    payload: DispenseCreateRequest
  ): Promise<DispenseResponse> {
    const response = await client.post(
      `/v1/pharmacy/prescriptions/${prescriptionId}/dispense`,
      payload
    );
    return response.data;
  },

  async fulfillPrescriptionExternal(
    prescriptionId: string,
    payload: ExternalFulfillCreateRequest
  ): Promise<PrescriptionFulfillmentResponse> {
    const response = await client.post(
      `/v1/pharmacy/prescriptions/${prescriptionId}/fulfill-external`,
      payload
    );
    return response.data;
  },
};
