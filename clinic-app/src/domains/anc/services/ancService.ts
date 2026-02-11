import client from '@/api/client';
import { PurposeOfUse, VisitStatus } from '@/shared/enums';
import { VisitResponse } from '@/shared/types';
import { AxiosError } from 'axios';

export interface PregnancyEpisodeCreate {
  lmp_date?: string | null;
  edd_date?: string | null;
  gravida?: number | null;
  parity?: number | null;
  booking_reg_no?: string | null;
  past_medical_history?: string | null;
  past_surgical_history?: string | null;
  history_present_pregnancy?: string | null;
  general_exam?: string | null;
  close_existing?: boolean;
}

export interface PregnancyEpisodeResponse extends PregnancyEpisodeCreate {
  id: string;
  clinic_id: string;
  patient_id: string;
  status: 'ACTIVE' | 'CLOSED';
  created_by: string;
  created_at: string;
  closed_at?: string | null;
}

export interface PreviousPregnancyCreate {
  year?: number | null;
  duration?: string | null;
  antenatal_complications?: string | null;
  labour?: string | null;
  age_alive?: string | null;
  age_dead?: string | null;
  cause_of_death?: string | null;
}

export interface PreviousPregnancyResponse extends PreviousPregnancyCreate {
  id: string;
  clinic_id: string;
  episode_id: string;
  created_by: string;
  created_at: string;
}

export interface ANCEncounterUpsert {
  action?: 'SAVE_DRAFT' | 'SIGN';
  episode_id: string;
  fundus_height?: string | null;
  presentation_position?: string | null;
  presenting_part?: string | null;
  foetal_heart?: string | null;
  bp_systolic?: number | null;
  bp_diastolic?: number | null;
  urine?: string | null;
  weight_kg?: number | null;
  remarks?: string | null;
  ref?: string | null;
  initial?: string | null;
}

export interface ANCEncounterResponse extends ANCEncounterUpsert {
  id: string;
  clinic_id: string;
  visit_id: string;
  recorded_by: string;
  recorded_at: string;
  record_status: 'DRAFT' | 'SIGNED' | 'AMENDED' | 'VOIDED';
  signed_at?: string | null;
  void_reason?: string | null;
}

export interface ANCExportOptions {
  purpose_of_use: PurposeOfUse;
  justification: string;
  include_previous_pregnancies?: boolean;
  include_encounters?: boolean;
  include_blank_rows?: number;
  format?: 'A4';
  orientation?: 'PORTRAIT';
}

const purpose_of_use = PurposeOfUse.TREATMENT;

export const ancService = {
  async getQueue(status?: VisitStatus): Promise<VisitResponse[]> {
    const params = status ? { status } : undefined;
    const response = await client.get('/v1/anc/queue', { params });
    return response.data;
  },

  async createEpisode(
    patientId: string,
    payload: PregnancyEpisodeCreate
  ): Promise<PregnancyEpisodeResponse> {
    const response = await client.post(
      `/v1/anc/patients/${patientId}/episodes`,
      payload
    );
    return response.data;
  },

  async getActiveEpisode(patientId: string): Promise<PregnancyEpisodeResponse | null> {
    try {
      const response = await client.get('/v1/anc/episodes/active', {
        params: {
          patient_id: patientId,
          purpose_of_use,
          justification: 'ANC episode lookup',
        },
      });
      return response.data ?? null;
    } catch (err) {
      const axiosErr = err as AxiosError;
      if (axiosErr.response?.status === 404) {
        return null;
      }
      throw err;
    }
  },

  async getEpisode(episodeId: string): Promise<PregnancyEpisodeResponse> {
    const response = await client.get(`/v1/anc/episodes/${episodeId}`, {
      params: {
        purpose_of_use,
        justification: 'ANC episode view',
      },
    });
    return response.data;
  },

  async listPreviousPregnancies(
    episodeId: string
  ): Promise<PreviousPregnancyResponse[]> {
    const response = await client.get(
      `/v1/anc/episodes/${episodeId}/previous-pregnancies`,
      {
        params: {
          purpose_of_use,
          justification: 'ANC previous pregnancies',
        },
      }
    );
    return response.data;
  },

  async addPreviousPregnancy(
    episodeId: string,
    payload: PreviousPregnancyCreate
  ): Promise<PreviousPregnancyResponse> {
    const response = await client.post(
      `/v1/anc/episodes/${episodeId}/previous-pregnancies`,
      payload
    );
    return response.data;
  },

  async getEncounter(visitId: string): Promise<ANCEncounterResponse | null> {
    try {
      const response = await client.get(`/v1/anc/visits/${visitId}/encounter`, {
        params: {
          purpose_of_use,
          justification: 'ANC encounter view',
        },
      });
      return response.data ?? null;
    } catch (err) {
      const axiosErr = err as AxiosError;
      if (axiosErr.response?.status === 404) {
        return null;
      }
      throw err;
    }
  },

  async upsertEncounter(
    visitId: string,
    payload: ANCEncounterUpsert
  ): Promise<ANCEncounterResponse> {
    const response = await client.post(
      `/v1/anc/visits/${visitId}/encounter`,
      payload
    );
    return response.data;
  },

  async exportEpisodePdf(
    episodeId: string,
    options: ANCExportOptions
  ): Promise<Blob> {
    const response = await client.get(`/v1/anc/episodes/${episodeId}/export.pdf`, {
      params: {
        purpose_of_use: options.purpose_of_use,
        justification: options.justification,
        include_previous_pregnancies: options.include_previous_pregnancies ?? true,
        include_encounters: options.include_encounters ?? true,
        include_blank_rows: options.include_blank_rows ?? 0,
        format: options.format ?? 'A4',
        orientation: options.orientation ?? 'PORTRAIT',
      },
      responseType: 'blob',
    });
    return response.data as Blob;
  },
};
