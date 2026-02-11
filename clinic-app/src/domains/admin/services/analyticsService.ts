import client from '@/api/client';

export interface StaffActivityBucket {
  hour: string;
  activity_type: 'visit_registration' | 'consultation_started';
  actor_role: string;
  count: number;
}

export interface SystemPerformanceMetrics {
  avg_triage_wait_minutes: number | null;
  triage_samples: number;
  avg_consult_wait_minutes: number | null;
  consult_samples: number;
  avg_lab_turnaround_minutes: number | null;
  lab_samples: number;
}

export const analyticsService = {
  async getStaffActivity(days = 7): Promise<StaffActivityBucket[]> {
    const response = await client.get('/v1/admin/staff-activity', { params: { days } });
    return response.data;
  },
  async getSystemMetrics(): Promise<SystemPerformanceMetrics> {
    const response = await client.get('/v1/admin/system-metrics');
    return response.data;
  },
};
