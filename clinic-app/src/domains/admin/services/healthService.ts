import client from '@/api/client';

export interface ClinicHealthSnapshot {
  active_visits: number;
  active_staff: number;
  break_glass_24h: number;
}

export const healthService = {
  async getSnapshot(): Promise<ClinicHealthSnapshot> {
    const response = await client.get('/v1/admin/clinic-health');
    return response.data;
  },
};
