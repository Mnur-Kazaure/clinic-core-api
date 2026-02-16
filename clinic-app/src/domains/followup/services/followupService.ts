import client from '@/api/client';

export type RecallIntervalUnit = 'DAYS' | 'WEEKS' | 'MONTHS';
export type FollowUpPriority = 'ROUTINE' | 'IMPORTANT' | 'CRITICAL';
export type DiagnosisSystem = 'ICD10' | 'ICPC2' | 'LOCAL';
export type DiagnosisMappingConfidence = 'HIGH' | 'MEDIUM';

export interface ConditionProfile {
  id: string;
  clinic_id: string;
  code: string;
  display_name: string;
  recall_enabled: boolean;
  default_interval_value: number;
  default_interval_unit: RecallIntervalUnit;
  default_priority: FollowUpPriority;
  cooldown_days: number;
  keyword_synonyms: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ConditionProfileCreatePayload {
  code: string;
  display_name: string;
  recall_enabled: boolean;
  default_interval_value: number;
  default_interval_unit: RecallIntervalUnit;
  default_priority: FollowUpPriority;
  cooldown_days: number;
  keyword_synonyms: string[];
  justification: string;
}

export interface ConditionProfileUpdatePayload {
  display_name?: string;
  recall_enabled?: boolean;
  default_interval_value?: number;
  default_interval_unit?: RecallIntervalUnit;
  default_priority?: FollowUpPriority;
  cooldown_days?: number;
  keyword_synonyms?: string[];
  justification: string;
}

export interface DiagnosisConditionMap {
  id: string;
  clinic_id: string;
  diagnosis_system: DiagnosisSystem;
  diagnosis_code: string;
  condition_profile_id: string;
  confidence: DiagnosisMappingConfidence;
  active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface DiagnosisMappingCreatePayload {
  diagnosis_system: DiagnosisSystem;
  diagnosis_code: string;
  condition_profile_id: string;
  confidence: DiagnosisMappingConfidence;
  justification: string;
}

export interface DiagnosisMappingActivePayload {
  active: boolean;
  justification: string;
}

export interface CreateChronicRecallPayload {
  patient_id: string;
  condition_profile_id: string;
  origin_visit_id?: string;
  interval_value_override?: number;
  interval_unit_override?: RecallIntervalUnit;
  justification: string;
}

export interface FollowUpListItem {
  id: string;
  clinic_id: string;
  patient_id_canonical: string;
  patient_name?: string | null;
  patient_mrn?: string | null;
  type: 'MANUAL' | 'POST_DISCHARGE' | 'LAB_REVIEW' | 'ANC_REVIEW' | 'CHRONIC_RECALL';
  priority: FollowUpPriority;
  status: 'SCHEDULED' | 'COMPLETED' | 'MISSED' | 'CANCELLED';
  due_at: string;
  reason: string;
  owner_user_id: string;
  owner_user_name?: string | null;
  owner_role: string;
  recommended_service_line: 'OPD' | 'ANC' | 'MATERNITY';
  active_visit_id?: string | null;
  linked_visit_id?: string | null;
}

export interface ClinicianFollowUpDashboard {
  overdue: FollowUpListItem[];
  today: FollowUpListItem[];
  upcoming: FollowUpListItem[];
}

export interface ReceptionFollowUpDashboard {
  today: FollowUpListItem[];
  tomorrow: FollowUpListItem[];
}

export interface FollowUpReschedulePayload {
  due_at: string;
  reason: string;
  justification: string;
}

export interface FollowUpRescheduleResponse {
  original_follow_up_id: string;
  replacement: FollowUpListItem;
}

export const followUpService = {
  async listConditionProfiles(): Promise<ConditionProfile[]> {
    const response = await client.get('/v1/condition-profiles');
    return response.data;
  },

  async createConditionProfile(
    payload: ConditionProfileCreatePayload
  ): Promise<ConditionProfile> {
    const response = await client.post('/v1/condition-profiles', payload);
    return response.data;
  },

  async updateConditionProfile(
    profileId: string,
    payload: ConditionProfileUpdatePayload
  ): Promise<ConditionProfile> {
    const response = await client.patch(`/v1/condition-profiles/${profileId}`, payload);
    return response.data;
  },

  async listDiagnosisMappings(): Promise<DiagnosisConditionMap[]> {
    const response = await client.get('/v1/diagnosis-mappings');
    return response.data;
  },

  async createDiagnosisMapping(
    payload: DiagnosisMappingCreatePayload
  ): Promise<DiagnosisConditionMap> {
    const response = await client.post('/v1/diagnosis-mappings', payload);
    return response.data;
  },

  async setDiagnosisMappingActive(
    mappingId: string,
    payload: DiagnosisMappingActivePayload
  ): Promise<DiagnosisConditionMap> {
    const response = await client.patch(
      `/v1/diagnosis-mappings/${mappingId}/active`,
      payload
    );
    return response.data;
  },

  async createChronicRecall(payload: CreateChronicRecallPayload): Promise<void> {
    await client.post('/v1/chronic-recalls', payload);
  },

  async getMyFollowUps(): Promise<ClinicianFollowUpDashboard> {
    const response = await client.get('/v1/follow-ups/my', {
      params: {
        purpose_of_use: 'TREATMENT',
        justification: 'Clinician follow-up dashboard',
      },
    });
    return response.data;
  },

  async getReceptionFollowUps(): Promise<ReceptionFollowUpDashboard> {
    const response = await client.get('/v1/follow-ups/reception', {
      params: {
        purpose_of_use: 'OPERATIONS',
        justification: 'Reception follow-up dashboard',
      },
    });
    return response.data;
  },

  async rescheduleFollowUp(
    followUpId: string,
    payload: FollowUpReschedulePayload
  ): Promise<FollowUpRescheduleResponse> {
    const response = await client.post(
      `/v1/follow-ups/${followUpId}/reschedule`,
      payload
    );
    return response.data;
  },
};
