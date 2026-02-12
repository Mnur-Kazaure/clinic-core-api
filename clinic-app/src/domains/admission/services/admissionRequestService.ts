import client from '@/api/client';

export type AdmissionType = 'EMERGENCY' | 'ELECTIVE';
export type AdmissionRequestStatus =
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'CANCELLED';
export type AdmissionStatus = 'ACTIVE' | 'DISCHARGED' | 'CANCELLED';

export interface AdmissionRequest {
  id: string;
  clinic_id: string;
  patient_id: string;
  admission_type: AdmissionType;
  status: AdmissionRequestStatus;
  reason: string;
  requested_by: string;
  requested_at: string;
  decided_by?: string | null;
  decided_at?: string | null;
  decision_reason?: string | null;
  admission_id?: string | null;
  admission_status?: AdmissionStatus | null;
  has_active_bed_assignment?: boolean;
  current_bed_id?: string | null;
  current_bed_label?: string | null;
}

export interface AdmissionRequestCreatePayload {
  patient_id: string;
  admission_type: AdmissionType;
  reason: string;
}

export interface AdmissionRequestDecisionPayload {
  reason: string;
}

export const admissionRequestService = {
  async createRequest(payload: AdmissionRequestCreatePayload): Promise<AdmissionRequest> {
    const response = await client.post('/v1/admissions/requests', payload);
    return response.data;
  },

  async listRequests(status?: AdmissionRequestStatus): Promise<AdmissionRequest[]> {
    const response = await client.get('/v1/admissions/requests', {
      params: status ? { status_filter: status } : undefined,
    });
    return response.data;
  },

  async approveRequest(
    requestId: string,
    payload: AdmissionRequestDecisionPayload
  ): Promise<AdmissionRequest> {
    const response = await client.post(
      `/v1/admissions/requests/${requestId}/approve`,
      payload
    );
    return response.data;
  },

  async rejectRequest(
    requestId: string,
    payload: AdmissionRequestDecisionPayload
  ): Promise<AdmissionRequest> {
    const response = await client.post(
      `/v1/admissions/requests/${requestId}/reject`,
      payload
    );
    return response.data;
  },

  async cancelRequest(
    requestId: string,
    payload: AdmissionRequestDecisionPayload
  ): Promise<AdmissionRequest> {
    const response = await client.post(
      `/v1/admissions/requests/${requestId}/cancel`,
      payload
    );
    return response.data;
  },
};
