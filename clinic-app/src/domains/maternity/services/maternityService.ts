import client from '@/api/client';
import { PurposeOfUse, VisitStatus } from '@/shared/enums';
import { VisitResponse } from '@/shared/types';

export interface MaternityDeliveryUpsert {
  action?: 'SAVE_DRAFT' | 'SIGN';
  episode_id?: string | null;
  delivered_at?: string | null;
  mode_of_delivery?: 'SVD' | 'C_SECTION' | 'ASSISTED' | 'UNKNOWN';
  outcome?: 'LIVE_BIRTH' | 'STILLBIRTH' | 'NEONATAL_DEATH' | 'UNKNOWN';
  baby_sex?: 'MALE' | 'FEMALE' | 'UNKNOWN';
  baby_weight_kg?: number | null;
  apgar_1?: number | null;
  apgar_5?: number | null;
  maternal_complications?: string | null;
  newborn_complications?: string | null;
  notes?: string | null;
}

export interface MaternityDeliveryResponse extends MaternityDeliveryUpsert {
  id: string;
  clinic_id: string;
  visit_id: string;
  recorded_by: string;
  recorded_at: string;
  record_status: 'DRAFT' | 'SIGNED' | 'AMENDED' | 'VOIDED';
  signed_at?: string | null;
  void_reason?: string | null;
}

export interface PostnatalNoteCreate {
  subject: 'MOTHER' | 'BABY';
  note: string;
}

export interface PostnatalNoteResponse extends PostnatalNoteCreate {
  id: string;
  clinic_id: string;
  visit_id: string;
  added_by: string;
  added_at: string;
}

export interface FamilyPlanningEventCreate {
  commodity: 'IMPLANT' | 'IUD' | 'INJECTABLE' | 'PILL' | 'CONDOM' | 'OTHER';
  notes?: string | null;
}

export interface FamilyPlanningEventResponse extends FamilyPlanningEventCreate {
  id: string;
  clinic_id: string;
  visit_id: string;
  added_by: string;
  added_at: string;
}

const purpose_of_use = PurposeOfUse.TREATMENT;

export const maternityService = {
  async getQueue(status?: VisitStatus): Promise<VisitResponse[]> {
    const params = status ? { status } : undefined;
    const response = await client.get('/v1/maternity/queue', { params });
    return response.data;
  },

  async getDelivery(visitId: string): Promise<MaternityDeliveryResponse | null> {
    const response = await client.get(`/v1/maternity/visits/${visitId}/delivery`, {
      params: {
        purpose_of_use,
        justification: 'Maternity delivery view',
      },
    });
    return response.data ?? null;
  },

  async upsertDelivery(
    visitId: string,
    payload: MaternityDeliveryUpsert
  ): Promise<MaternityDeliveryResponse> {
    const response = await client.post(
      `/v1/maternity/visits/${visitId}/delivery`,
      payload
    );
    return response.data;
  },

  async listPostnatalNotes(visitId: string): Promise<PostnatalNoteResponse[]> {
    const response = await client.get(
      `/v1/maternity/visits/${visitId}/postnatal-notes`,
      {
        params: {
          purpose_of_use,
          justification: 'Maternity postnatal notes',
        },
      }
    );
    return response.data;
  },

  async addPostnatalNote(
    visitId: string,
    payload: PostnatalNoteCreate
  ): Promise<PostnatalNoteResponse> {
    const response = await client.post(
      `/v1/maternity/visits/${visitId}/postnatal-notes`,
      payload
    );
    return response.data;
  },

  async listFamilyPlanningEvents(
    visitId: string
  ): Promise<FamilyPlanningEventResponse[]> {
    const response = await client.get(
      `/v1/maternity/visits/${visitId}/family-planning`,
      {
        params: {
          purpose_of_use,
          justification: 'Maternity family planning',
        },
      }
    );
    return response.data;
  },

  async addFamilyPlanningEvent(
    visitId: string,
    payload: FamilyPlanningEventCreate
  ): Promise<FamilyPlanningEventResponse> {
    const response = await client.post(
      `/v1/maternity/visits/${visitId}/family-planning`,
      payload
    );
    return response.data;
  },
};
