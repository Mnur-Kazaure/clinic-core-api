// /projects/clinic-monorepo/clinic-app/src/domains/visit/services/visitService.ts
import client from '@/api/client';
import { PurposeOfUse, VisitStatus, VisitServiceLine } from '@/shared/enums';
import { VisitResponse } from '@/shared/types';
import { v4 as uuidv4 } from 'uuid';

export interface VisitCreateRequest {
  patient_id: string;
  assigned_doctor_id: string;
  service_line?: VisitServiceLine;
}

export type VisitCreateResponse = VisitResponse;

export interface VisitTransitionRequest {
  to_status: VisitStatus;
  expected_version: number;
  mode?: 'normal' | 'override';
  override_reason_code?: string;
  override_reason_text?: string;
}

export interface VisitReassignRequest {
  assigned_doctor_id: string;
  expected_version: number;
  service_line?: VisitServiceLine;
  reason?: string;
}

export interface VisitIntakeFlagRequest {
  flagged: boolean;
  reason: string;
}

export interface VisitTimelineEvent {
  id: string;
  from_status: VisitStatus;
  to_status: VisitStatus;
  changed_by: string;
  created_at: string;
}

export interface VisitTimelineResponse {
  visit_id: string;
  timeline: VisitTimelineEvent[];
}

export interface AllowedTransitionsResponse {
  allowed: VisitStatus[];
}

export const visitService = {
  // Start new visit
  async startVisit(payload: VisitCreateRequest): Promise<VisitResponse> {
    const response = await client.post('/v1/visits/start', payload);
    return response.data;
  },

  // Get reception queue
  async getQueue(status?: string): Promise<VisitResponse[]> {
    const params = {
      ...(status ? { status } : {}),
      purpose_of_use: PurposeOfUse.OPERATIONS,
      justification: 'Reception visit queue',
    };
    const response = await client.get('/v1/visits/queue', { params });
    return response.data;
  },

  // Get doctor's assigned visits
  async getDoctorQueue(status?: string): Promise<VisitResponse[]> {
    const params = {
      ...(status ? { status } : {}),
      purpose_of_use: PurposeOfUse.TREATMENT,
      justification: 'Doctor visit queue',
    };
    const response = await client.get('/v1/visits/doctor-queue', { params });
    return response.data;
  },

  // Get visit details
  async getVisit(
    visitId: string,
    options?: {
      purpose_of_use?: PurposeOfUse;
      justification?: string;
    }
  ): Promise<VisitResponse> {
    const purpose_of_use = options?.purpose_of_use ?? PurposeOfUse.OPERATIONS;
    const justification = options?.justification ?? 'Reception visit view';
    const response = await client.get(`/v1/visits/${visitId}`, {
      params: {
        purpose_of_use,
        justification,
      },
    });
    return response.data;
  },

  // Get active visit for a patient
  async getActiveVisit(patientId: string): Promise<VisitResponse | null> {
    const response = await client.get('/v1/visits/active', {
      params: {
        patient_id: patientId,
        purpose_of_use: PurposeOfUse.OPERATIONS,
        justification: 'Reception active visit check',
      },
    });
    return response.data ?? null;
  },

  // Get recent visits for reception activity
  async getRecentVisits(limit = 10): Promise<VisitResponse[]> {
    const response = await client.get('/v1/visits/recent', {
      params: {
        limit,
        purpose_of_use: PurposeOfUse.OPERATIONS,
        justification: 'Reception recent visits',
      },
    });
    return response.data;
  },

  // Get visit timeline
  async getVisitTimeline(
    visitId: string,
    purposeOfUse: PurposeOfUse = PurposeOfUse.OPERATIONS
  ): Promise<VisitTimelineResponse> {
    const response = await client.get(`/v1/visits/${visitId}/timeline`, {
      params: {
        purpose_of_use: purposeOfUse,
        justification: 'Visit timeline review',
      },
    });
    return response.data;
  },

  // Get allowed transitions
  async getAllowedTransitions(visitId: string): Promise<AllowedTransitionsResponse> {
    const response = await client.get(`/v1/visits/${visitId}/allowed-transitions`, {
      params: {
        purpose_of_use: PurposeOfUse.OPERATIONS,
        justification: 'Visit transition validation',
      },
    });
    return response.data;
  },

  // Transition visit status
  async transitionVisit(
    visitId: string,
    payload: VisitTransitionRequest
  ): Promise<VisitResponse> {
    const idempotencyKey = `visit-transition-${visitId}-${payload.to_status}-${uuidv4()}`;
    const response = await client.post(`/v1/visits/${visitId}/transition`, {
      ...payload,
    }, {
      headers: {
        'Idempotency-Key': idempotencyKey,
      },
    });
    return response.data;
  },

  async recheckAutoComplete(visitId: string): Promise<VisitResponse> {
    const response = await client.post(`/v1/visits/${visitId}/auto-complete`);
    return response.data;
  },

  async reassignOwner(
    visitId: string,
    payload: VisitReassignRequest
  ): Promise<VisitResponse> {
    const response = await client.post(
      `/v1/visits/${visitId}/reassign-owner`,
      payload
    );
    return response.data;
  },

  async setIntakeFlag(
    visitId: string,
    payload: VisitIntakeFlagRequest
  ): Promise<VisitResponse> {
    const response = await client.post(`/v1/visits/${visitId}/intake-flag`, payload);
    return response.data;
  },
};
