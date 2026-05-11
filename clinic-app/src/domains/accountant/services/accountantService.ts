import client from '@/api/client';
import { BillingReasonCode } from '@/domains/billing/services/billingWorkflowService';

export interface AccountantOverview {
  date: string;
  currency: string;
  revenue_today_minor: number;
  revenue_this_month_minor: number;
  outstanding_bills_minor: number;
  refunds_today_minor: number;
  net_revenue_minor: number;
}

export interface DepartmentRevenueItem {
  department_id?: string | null;
  department_name: string;
  revenue_minor: number;
  percentage: number;
}

export interface PaymentMethodAnalysisItem {
  payment_method: BillingReasonCode;
  total_minor: number;
  count: number;
  percentage: number;
}

export interface CashierSessionSummary {
  id: string;
  cashier_id: string;
  cashier_name?: string | null;
  status: string;
  shift_start: string;
  shift_end?: string | null;
  expected_total_minor: number;
  counted_total_minor?: number | null;
  variance_minor?: number | null;
  closing_note?: string | null;
  currency: string;
}

export interface CashierSessionListResponse {
  data: CashierSessionSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface CashierSessionTransaction {
  id: string;
  transaction_type: 'PAYMENT' | 'REFUND';
  occurred_at: string;
  reference: string;
  patient_name?: string | null;
  amount_minor: number;
  currency: string;
  payment_method?: BillingReasonCode | null;
  actor_name?: string | null;
  note?: string | null;
}

export interface CashierSessionDetail {
  session: CashierSessionSummary;
  payments_total_minor: number;
  refunds_total_minor: number;
  net_total_minor: number;
  transactions: CashierSessionTransaction[];
}

export interface AccountantRefundRow {
  id: string;
  receipt_id: string;
  receipt_number: string;
  patient_name?: string | null;
  cashier_name?: string | null;
  amount_minor: number;
  currency: string;
  reason: string;
  status: string;
  processed_at: string;
}

export interface AccountantRefundListResponse {
  data: AccountantRefundRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface OutstandingBillRow {
  patient_id: string;
  patient_name?: string | null;
  outstanding_minor: number;
  currency: string;
  visits_count: number;
  last_visit_id?: string | null;
}

export interface OutstandingBillListResponse {
  data: OutstandingBillRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface RefundReason {
  id: string;
  reason_code: string;
  description?: string | null;
  is_active: boolean;
}

export interface AccountantAuditFeedRow {
  id: string;
  event_type: string;
  occurred_at: string;
  actor_name?: string | null;
  amount_minor?: number | null;
  currency?: string | null;
  reference?: string | null;
  detail?: string | null;
  severity: 'info' | 'warning';
}

export interface AccountantAuditFeedResponse {
  data: AccountantAuditFeedRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface FraudSignals {
  date: string;
  currency: string;
  large_refunds_count: number;
  reprints_today_count: number;
  open_variances_count: number;
  cash_total_today_minor: number;
  high_cash_today: boolean;
  thresholds: Record<string, number>;
}

export interface CashierSessionReconcilePayload {
  counted_total_minor?: number;
  closing_note?: string;
}

export interface CashierSessionReconcileResponse {
  session_id: string;
  status: string;
  counted_total_minor?: number | null;
  variance_minor?: number | null;
  reconciled_at: string;
}

export const accountantService = {
  async getOverview(forDate?: string): Promise<AccountantOverview> {
    const params = forDate ? { for_date: forDate } : undefined;
    const response = await client.get('/v1/accountant/overview', { params });
    return response.data;
  },

  async getRevenueByDepartment(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<DepartmentRevenueItem[]> {
    const response = await client.get('/v1/accountant/revenue-by-department', { params });
    return response.data;
  },

  async getPaymentMethods(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<PaymentMethodAnalysisItem[]> {
    const response = await client.get('/v1/accountant/payment-methods', { params });
    return response.data;
  },

  async listCashierSessions(params?: {
    status?: string;
    date?: string;
    cashier_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<CashierSessionListResponse> {
    const response = await client.get('/v1/accountant/cashier-sessions', { params });
    return response.data;
  },

  async getCashierSession(sessionId: string): Promise<CashierSessionDetail> {
    const response = await client.get(`/v1/accountant/cashier-sessions/${sessionId}`);
    return response.data;
  },

  async reconcileCashierSession(
    sessionId: string,
    payload: CashierSessionReconcilePayload
  ): Promise<CashierSessionReconcileResponse> {
    const response = await client.post(
      `/v1/accountant/cashier-sessions/${sessionId}/reconcile`,
      payload,
      {
        headers: {
          'Idempotency-Key':
            typeof crypto !== 'undefined' && 'randomUUID' in crypto
              ? crypto.randomUUID()
              : `${Date.now()}-${sessionId}`,
        },
      }
    );
    return response.data;
  },

  async listRefunds(params?: {
    start_date?: string;
    end_date?: string;
    cashier_id?: string;
    min_amount_minor?: number;
    limit?: number;
    offset?: number;
  }): Promise<AccountantRefundListResponse> {
    const response = await client.get('/v1/accountant/refunds', { params });
    return response.data;
  },

  async listRefundReasons(includeInactive = false): Promise<RefundReason[]> {
    const response = await client.get('/v1/accountant/refund-reasons', {
      params: { include_inactive: includeInactive },
    });
    return response.data;
  },

  async listOutstanding(params?: {
    department_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<OutstandingBillListResponse> {
    const response = await client.get('/v1/accountant/outstanding', { params });
    return response.data;
  },

  async getAuditFeed(params?: {
    limit?: number;
    offset?: number;
  }): Promise<AccountantAuditFeedResponse> {
    const response = await client.get('/v1/accountant/audit-feed', { params });
    return response.data;
  },

  async getFraudSignals(forDate?: string): Promise<FraudSignals> {
    const params = forDate ? { for_date: forDate } : undefined;
    const response = await client.get('/v1/accountant/fraud-signals', { params });
    return response.data;
  },

  async downloadCsv(params?: {
    start_date?: string;
    end_date?: string;
    payment_method?: BillingReasonCode;
  }): Promise<Blob> {
    const response = await client.get('/v1/accountant/reports/export', {
      params,
      responseType: 'blob',
    });
    return response.data as Blob;
  },
};
