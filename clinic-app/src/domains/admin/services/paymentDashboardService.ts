import client from '@/api/client';

export interface PaymentDashboardOverview {
  currency: string;
  today_revenue_minor: number;
  monthly_target_minor: number;
  monthly_progress_pct: number;
  outstanding_minor: number;
  collection_rate_pct: number;
  transactions_today: number;
  avg_transaction_minor: number;
  peak_hour: string | null;
}

export interface TransactionVelocityItem {
  occurred_at: string;
  amount_minor: number;
}

export interface PaymentTransactionItem {
  occurred_at: string;
  patient_name?: string | null;
  service: string;
  amount_minor: number;
  method?: string | null;
  status: string;
  note?: string | null;
}

export interface PaymentCategoryItem {
  category: string;
  amount_minor: number;
  percent: number;
}

export interface PaymentMethodItem {
  method: string;
  amount_minor: number;
  percent: number;
}

export interface TopServiceItem {
  service: string;
  amount_minor: number;
  count: number;
}

export interface PaymentAlertItem {
  severity: string;
  message: string;
}

export interface OutstandingBalanceItem {
  patient_id: string;
  patient_name?: string | null;
  balance_minor: number;
  days_since_last_payment?: number | null;
}

export interface PaymentDashboardResponse {
  overview: PaymentDashboardOverview;
  velocity: TransactionVelocityItem[];
  transactions: PaymentTransactionItem[];
  category_breakdown: PaymentCategoryItem[];
  top_services: TopServiceItem[];
  method_breakdown: PaymentMethodItem[];
  alerts: PaymentAlertItem[];
  insights: string[];
  outstanding_balances: OutstandingBalanceItem[];
}

export const paymentDashboardService = {
  async getDashboard(): Promise<PaymentDashboardResponse> {
    const response = await client.get('/v1/admin/payment-dashboard');
    return response.data;
  },
};
