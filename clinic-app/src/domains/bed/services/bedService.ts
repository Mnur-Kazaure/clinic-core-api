import client from '@/api/client';

export type BedStatus = 'AVAILABLE' | 'OUT_OF_SERVICE';

export interface Ward {
  id: string;
  clinic_id: string;
  name: string;
  ward_type: string;
  active: boolean;
  bed_label_prefix?: string | null;
  bed_label_padding?: number | null;
  bed_label_next?: number | null;
}

export interface Bed {
  id: string;
  clinic_id: string;
  ward_id: string;
  bed_label: string;
  status: BedStatus;
  active: boolean;
}

export interface WardCreatePayload {
  name: string;
  ward_type: string;
}

export interface WardBedRangePayload {
  name: string;
  ward_type: string;
  label_prefix: string;
  label_from: number;
  label_to: number;
  label_padding?: number;
}

export interface WardBedRangePreview {
  name: string;
  ward_type: string;
  label_prefix: string;
  label_from: number;
  label_to: number;
  label_padding: number;
  total_beds: number;
  bed_labels: string[];
  conflicts: string[];
  is_valid: boolean;
}

export interface WardBedRangeCreateResponse {
  ward: Ward;
  created_beds: number;
  bed_labels: string[];
}

export interface WardAppendBedResponse {
  ward_id: string;
  bed_id: string;
  bed_label: string;
  next_number?: number | null;
}

export interface WardRetireBedPayload {
  reason: string;
}

export interface WardRetireBedResponse {
  ward_id: string;
  bed_id: string;
  bed_label: string;
}

export interface BedCreatePayload {
  ward_id: string;
  bed_label: string;
  status: BedStatus;
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

export interface BedStatusUpdatePayload {
  status: BedStatus;
  reason?: string | null;
}

export interface BedActiveUpdatePayload {
  active: boolean;
  reason?: string | null;
}

export interface WardActiveUpdatePayload {
  active: boolean;
  reason?: string | null;
}

export type BedBoardOccupancyStatus =
  | 'AVAILABLE'
  | 'OCCUPIED'
  | 'OUT_OF_SERVICE'
  | 'INACTIVE';

export interface BedBoardOccupant {
  admission_id: string;
  patient_id: string;
  patient_name?: string | null;
  patient_mrn?: string | null;
  assigned_at: string;
}

export interface BedBoardBed {
  bed_id: string;
  bed_label: string;
  bed_status: BedStatus;
  bed_active: boolean;
  occupancy_status: BedBoardOccupancyStatus;
  active_assignment_id?: string | null;
  occupant?: BedBoardOccupant | null;
}

export interface BedBoardWardSummary {
  ward_id: string;
  ward_name: string;
  ward_type: string;
  ward_active: boolean;
  total_beds: number;
  available_beds: number;
  occupied_beds: number;
  out_of_service_beds: number;
  inactive_beds: number;
}

export interface BedBoardWard {
  summary: BedBoardWardSummary;
  beds: BedBoardBed[];
}

export interface BedBoardTotals {
  total_beds: number;
  available_beds: number;
  occupied_beds: number;
  out_of_service_beds: number;
  inactive_beds: number;
}

export interface BedBoardResponse {
  wards: BedBoardWard[];
  totals: BedBoardTotals;
}

export interface OccupiedBedItem {
  bed_id: string;
  bed_label: string;
  ward_id: string;
  ward_name: string;
  admission_id: string;
  admission_type: string;
  patient_id: string;
  patient_name?: string | null;
  patient_mrn?: string | null;
  assigned_at: string;
}

export interface OccupiedBedSearchResponse {
  total: number;
  items: OccupiedBedItem[];
}

export interface OccupiedBedDetailResponse {
  admission_id: string;
  admission_type: string;
  patient_id: string;
  patient_name?: string | null;
  patient_mrn?: string | null;
  ward_name?: string | null;
  bed_label?: string | null;
  assigned_at?: string | null;
  timeline: Array<{
    assignment_id: string;
    assignment_type: string;
    bed_id: string;
    bed_label: string;
    ward_id: string;
    ward_name: string;
    assigned_at: string;
    released_at?: string | null;
    reason?: string | null;
    assigned_by: string;
    assigned_by_name?: string | null;
    from_bed_label?: string | null;
  }>;
}

export const bedService = {
  async listWards(): Promise<Ward[]> {
    const response = await client.get('/v1/wards');
    return response.data;
  },

  async createWard(payload: WardCreatePayload): Promise<Ward> {
    const response = await client.post('/v1/wards', payload);
    return response.data;
  },

  async previewWardBedRange(payload: WardBedRangePayload): Promise<WardBedRangePreview> {
    const response = await client.post('/v1/wards/range/preview', payload);
    return response.data;
  },

  async createWardWithBedRange(
    payload: WardBedRangePayload
  ): Promise<WardBedRangeCreateResponse> {
    const response = await client.post('/v1/wards/range', payload);
    return response.data;
  },

  async appendWardBed(wardId: string): Promise<WardAppendBedResponse> {
    const response = await client.post(`/v1/wards/${wardId}/beds/append`);
    return response.data;
  },

  async retireLastWardBed(
    wardId: string,
    payload: WardRetireBedPayload
  ): Promise<WardRetireBedResponse> {
    const response = await client.post(`/v1/wards/${wardId}/beds/retire-last`, payload);
    return response.data;
  },

  async updateWardActive(wardId: string, payload: WardActiveUpdatePayload): Promise<Ward> {
    const response = await client.post(`/v1/wards/${wardId}/active`, payload);
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

  async createBed(payload: BedCreatePayload): Promise<Bed> {
    const response = await client.post('/v1/beds', payload);
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

  async updateBedStatus(bedId: string, payload: BedStatusUpdatePayload): Promise<Bed> {
    const response = await client.post(`/v1/beds/${bedId}/status`, payload);
    return response.data;
  },

  async updateBedActive(bedId: string, payload: BedActiveUpdatePayload): Promise<Bed> {
    const response = await client.post(`/v1/beds/${bedId}/active`, payload);
    return response.data;
  },

  async getBedBoard(): Promise<BedBoardResponse> {
    const response = await client.get('/v1/bed-board');
    return response.data;
  },

  async searchOccupiedBeds(params?: {
    query?: string;
    wardId?: string;
    limit?: number;
    offset?: number;
  }): Promise<OccupiedBedSearchResponse> {
    const response = await client.get('/v1/bed-board/occupied', {
      params: {
        query: params?.query,
        ward_id: params?.wardId,
        limit: params?.limit,
        offset: params?.offset,
      },
    });
    return response.data;
  },

  async getOccupiedBedDetail(admissionId: string): Promise<OccupiedBedDetailResponse> {
    const response = await client.get(`/v1/bed-board/occupied/${admissionId}`);
    return response.data;
  },
};
