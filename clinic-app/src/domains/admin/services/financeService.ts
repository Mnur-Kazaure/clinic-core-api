// clinic-app/src/domains/admin/services/financeService.ts
import client from '@/api/client';

export interface PaymentOversight {
  currency: string;
  charges_today_minor: number;
  payments_today_minor: number;
  refunds_today_minor: number;
  writeoffs_today_minor: number;
  net_today_minor: number;
  registration_fee_count_today: number;
  registration_fee_total_minor: number;
}

export interface PatientMetrics {
  total_patients: number;
  registered_today: number;
}

export const financeService = {
  async getPaymentOversight(): Promise<PaymentOversight> {
    const response = await client.get('/v1/admin/payment-oversight');
    return response.data;
  },
  async getPatientMetrics(): Promise<PatientMetrics> {
    const response = await client.get('/v1/admin/patient-metrics');
    return response.data;
  },
};
