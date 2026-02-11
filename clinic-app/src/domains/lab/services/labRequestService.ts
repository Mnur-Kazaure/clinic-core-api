import client from '@/api/client';

export interface LabRequestCreateRequest {
  visit_id: string;
  test_name: string;
  special_instructions?: string | null;
}

export interface LabRequestResponse {
  id: string;
  visit_id: string;
  test_name: string;
  special_instructions?: string | null;
  status: 'PENDING' | 'COMPLETED' | 'CANCELLED';
  requested_by: string;
  created_at: string;
  completed_at: string | null;
}

export const labRequestService = {
  async createLabRequest(
    payload: LabRequestCreateRequest
  ): Promise<LabRequestResponse> {
    const response = await client.post('/v1/lab/requests', payload);
    return response.data;
  },
};
