import client from '@/api/client';
import { v4 as uuidv4 } from 'uuid';

export interface LabRequest {
  id: string;
  visit_id: string;
  test_name: string;
  status: 'PENDING' | 'COMPLETED' | 'CANCELLED';
  requested_by: string;
  created_at: string;
  completed_at: string | null;
}

export interface LabResultCreate {
  result_value: string;
  result_unit: string;
  reference_range: string;
  technician_id: string;
}

export interface LabResult {
  id: string;
  lab_request_id: string;
  result_value: string;
  result_unit: string;
  reference_range: string;
  technician_id: string;
  created_at: string;
}

export interface LabCompletionResponse {
  lab_request_id: string;
  status: 'COMPLETED';
  completed_at: string;
  visit_ready_for_transition: boolean;
  suggested_next_visit_status: 'LAB_COMPLETED';
}

export const labService = {
  async getRequests(
    status?: 'PENDING' | 'COMPLETED' | 'CANCELLED'
  ): Promise<LabRequest[]> {
    const params = status ? { status } : {};
    const response = await client.get('/v1/lab/requests', { params });
    return response.data;
  },

  async getResults(requestId: string): Promise<LabResult[]> {
    const response = await client.get(`/v1/lab/requests/${requestId}/results`);
    return response.data;
  },

  async recordResults(
    requestId: string,
    data: LabResultCreate
  ): Promise<LabResult> {
    const response = await client.post(
      `/v1/lab/requests/${requestId}/results`,
      data
    );
    return response.data;
  },

  async completeRequest(requestId: string): Promise<LabCompletionResponse> {
    const response = await client.post(`/v1/lab/requests/${requestId}/complete`);
    return response.data;
  },

  async completeVisitLab(visitId: string): Promise<any> {
    const idempotencyKey = `lab-complete-${visitId}-${uuidv4()}`;
    const response = await client.post(
      `/v1/visits/${visitId}/transition`,
      {
        to_status: 'LAB_COMPLETED',
      },
      {
        headers: {
          'Idempotency-Key': idempotencyKey,
        },
      }
    );
    return response.data;
  },
};
