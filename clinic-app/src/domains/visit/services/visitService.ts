// /projects/clinic-monorepo/clinic-app/src/domains/visit/services/visitService.ts
import client from '@/api/client';
import { VisitStatus } from '@/shared/enums';
import { VisitResponse } from '@/shared/types';
import { v4 as uuidv4 } from 'uuid';

export interface VisitCreateRequest {
  patient_id: string;
  assigned_doctor_id: string;
}

export interface VisitCreateResponse extends VisitResponse {}

export interface VisitTransitionRequest {
  to_status: VisitStatus;
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
    const params = status ? { status } : {};
    const response = await client.get('/v1/visits/queue', { params });
    return response.data;
  },

  // Get doctor's assigned visits
  async getDoctorQueue(status?: string): Promise<VisitResponse[]> {
    const params = status ? { status } : {};
    const response = await client.get('/v1/visits/doctor-queue', { params });
    return response.data;
  },

  // Get visit details
  async getVisit(visitId: string): Promise<VisitResponse> {
    const response = await client.get(`/v1/visits/${visitId}`);
    return response.data;
  },

  // Get recent visits for reception activity
  async getRecentVisits(limit = 10): Promise<VisitResponse[]> {
    const response = await client.get('/v1/visits/recent', {
      params: { limit },
    });
    return response.data;
  },

  // Get visit timeline
  async getVisitTimeline(visitId: string): Promise<VisitTimelineResponse> {
    const response = await client.get(`/v1/visits/${visitId}/timeline`);
    return response.data;
  },

  // Get allowed transitions
  async getAllowedTransitions(visitId: string): Promise<AllowedTransitionsResponse> {
    const response = await client.get(`/v1/visits/${visitId}/allowed-transitions`);
    return response.data;
  },

  // Transition visit status
  async transitionVisit(visitId: string, toStatus: string): Promise<VisitResponse> {
    const idempotencyKey = `visit-transition-${visitId}-${toStatus}-${uuidv4()}`;
    const response = await client.post(`/v1/visits/${visitId}/transition`, {
      to_status: toStatus,
    }, {
      headers: {
        'Idempotency-Key': idempotencyKey,
      },
    });
    return response.data;
  },
};
