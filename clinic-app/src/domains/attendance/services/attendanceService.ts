// clinic-app/src/domains/attendance/services/attendanceService.ts
import client from '@/api/client';

export interface AttendanceLog {
  id: string;
  user_id: string;
  punch_type: string;
  punched_at: string;
  hardware_ref: string | null;
  location: string | null;
}

export const attendanceService = {
  async listLogs(): Promise<AttendanceLog[]> {
    const response = await client.get('/v1/attendance/logs');
    return response.data;
  },

  async punch(payload: { user_id: string; punch_type: string; location?: string }): Promise<AttendanceLog> {
    const response = await client.post('/v1/attendance/punch', payload);
    return response.data;
  }
};
