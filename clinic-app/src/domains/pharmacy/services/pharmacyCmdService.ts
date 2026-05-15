import client from '@/api/client';
import type { PharmacyRefillRequestResponse } from '@/domains/pharmacy/services/pharmacyService';

export const pharmacyCmdService = {
  async getRefillRequests(params?: { status_filter?: string }): Promise<PharmacyRefillRequestResponse[]> {
    const response = await client.get('/v1/pharmacy-cmd/refill-requests', { params });
    return response.data;
  },

  async reviewRefillRequest(
    requestId: string,
    payload: { decision: 'APPROVE' | 'REJECT'; review_note?: string | null }
  ): Promise<PharmacyRefillRequestResponse> {
    const response = await client.post(
      `/v1/pharmacy-cmd/refill-requests/${requestId}/review`,
      payload
    );
    return response.data;
  },
};
