import client from '@/api/client';
import { LabRequest, LabResult } from '@/domains/lab/services/labService';

export const doctorLabService = {
  async getLabRequestsByVisit(visitId: string): Promise<LabRequest[]> {
    const response = await client.get(
      `/v1/doctor/visits/${visitId}/lab-requests`
    );
    return response.data;
  },

  async getLabResultsForRequest(requestId: string): Promise<LabResult[]> {
    const response = await client.get(
      `/v1/doctor/lab-requests/${requestId}/results`
    );
    return response.data;
  },
};
