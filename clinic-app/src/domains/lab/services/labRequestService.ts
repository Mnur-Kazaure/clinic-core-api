import client from '@/api/client';

export interface LabRequestCreateRequest {
  visit_id: string;
  test_name: string;
  test_code?: string | null;
  special_instructions?: string | null;
}

export interface LabRequestResponse {
  id: string;
  visit_id: string;
  test_name: string;
  test_code?: string | null;
  special_instructions?: string | null;
  status: 'PENDING' | 'COMPLETED' | 'CANCELLED';
  requested_by: string;
  billing_item_id?: string | null;
  billing_status?: string | null;
  billing_total_minor?: number | null;
  billing_currency?: string | null;
  payment_verified?: boolean | null;
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
