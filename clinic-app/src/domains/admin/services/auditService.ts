import client from '@/api/client';

export interface AuditTimelineItem {
  id: string;
  source: 'EVENT' | 'ACCESS';
  event_type: string;
  actor_id?: string | null;
  actor_role: string;
  clinic_id: string;
  patient_id?: string | null;
  resource?: string | null;
  break_glass?: boolean | null;
  occurred_at: string;
}

export interface AuditTimelineParams {
  from?: string;
  to?: string;
  event_type?: string;
  actor_id?: string;
  limit?: number;
}

export const auditService = {
  async getTimeline(params: AuditTimelineParams): Promise<AuditTimelineItem[]> {
    const response = await client.get('/v1/admin/audit-timeline', { params });
    return response.data;
  },
};
