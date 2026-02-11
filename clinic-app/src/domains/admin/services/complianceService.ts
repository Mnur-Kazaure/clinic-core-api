import client from '@/api/client';

export interface ComplianceSummary {
  break_glass_24h: number;
  open_audit_cases: number;
  failed_logins_24h: number;
}

export const complianceService = {
  async getSummary(): Promise<ComplianceSummary> {
    const response = await client.get('/v1/admin/compliance-summary');
    return response.data;
  },
};
