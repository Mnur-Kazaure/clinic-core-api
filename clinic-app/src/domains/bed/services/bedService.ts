import client from '@/api/client';

export type BedStatus = 'AVAILABLE' | 'OUT_OF_SERVICE';

export interface Ward {
  id: string;
  clinic_id: string;
  name: string;
  ward_type: string;
  active: boolean;
}

export interface Bed {
  id: string;
  clinic_id: string;
  ward_id: string;
  bed_label: string;
  status: BedStatus;
  active: boolean;
}

export interface BedAssignPayload {
  admission_id: string;
  bed_id: string;
  reason?: string | null;
}

export interface BedTransferPayload {
  admission_id: string;
  to_bed_id: string;
  reason: string;
}

export const bedService = {
  async listWards(): Promise<Ward[]> {
    const response = await client.get('/v1/wards');
    return response.data;
  },

  async listBeds(params?: { availableOnly?: boolean; wardId?: string }): Promise<Bed[]> {
    const response = await client.get('/v1/beds', {
      params: {
        available_only: params?.availableOnly ? true : undefined,
        ward_id: params?.wardId,
      },
    });
    return response.data;
  },

  async assignBed(payload: BedAssignPayload) {
    const response = await client.post('/v1/beds/assign', payload);
    return response.data;
  },

  async transferBed(payload: BedTransferPayload) {
    const response = await client.post('/v1/beds/transfer', payload);
    return response.data;
  },
};
