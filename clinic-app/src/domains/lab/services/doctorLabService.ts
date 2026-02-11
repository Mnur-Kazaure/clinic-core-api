import client from '@/api/client';
import { LabRequest, LabResult } from '@/domains/lab/services/labService';
import { PurposeOfUse } from '@/shared/enums';

export const doctorLabService = {
  async getLabRequestsByVisit(
    visitId: string,
    options?: {
      purpose_of_use?: PurposeOfUse;
      justification?: string;
      break_glass?: boolean;
    }
  ): Promise<LabRequest[]> {
    const purpose_of_use = options?.purpose_of_use ?? PurposeOfUse.TREATMENT;
    const justification = options?.justification ?? 'Lab review';
    const break_glass = options?.break_glass ?? false;
    const response = await client.get(
      `/v1/doctor/visits/${visitId}/lab-requests`,
      {
        params: {
          purpose_of_use,
          justification,
          break_glass,
        },
      }
    );
    return response.data;
  },

  async getLabResultsForRequest(
    requestId: string,
    options?: {
      purpose_of_use?: PurposeOfUse;
      justification?: string;
      break_glass?: boolean;
    }
  ): Promise<LabResult[]> {
    const purpose_of_use = options?.purpose_of_use ?? PurposeOfUse.TREATMENT;
    const justification = options?.justification ?? 'Lab review';
    const break_glass = options?.break_glass ?? false;
    const response = await client.get(
      `/v1/doctor/lab-requests/${requestId}/results`,
      {
        params: {
          purpose_of_use,
          justification,
          break_glass,
        },
      }
    );
    return response.data;
  },
};
