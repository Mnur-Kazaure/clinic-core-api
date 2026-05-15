import client from '@/api/client';

export type BillingReasonCode = 'CASH' | 'TRANSFER' | 'CARD';

export interface ChargeItemPrice {
  id: string;
  code: string;
  name: string;
  category: string;
  default_amount_minor: number;
  currency: string;
  active: boolean;
  display_order?: number | null;
  unit_id?: string | null;
  unit_name?: string | null;
}

export interface BillingPendingVisitSummary {
  visit_id: string;
  patient_id: string;
  patient_name?: string | null;
  currency: string;
  pending_items_count: number;
  pending_total_minor: number;
  latest_created_at?: string | null;
}

export interface BillingItem {
  id: string;
  clinic_id: string;
  patient_id: string;
  visit_id: string;
  cashier_pay_point_id?: string | null;
  charge_catalog_id?: string | null;
  charge_code?: string | null;
  item_name: string;
  service_type: string;
  quantity: number;
  unit_price_minor: number;
  total_minor: number;
  amount_paid_minor: number;
  currency: string;
  status: 'PENDING' | 'PAID' | 'WAIVED' | 'REFUNDED' | 'CANCELLED';
  created_by: string;
  payment_reference?: string | null;
  paid_at?: string | null;
  created_at: string;
}

export interface BillingPayRequest {
  visit_id: string;
  billing_item_ids: string[];
  cashier_pay_point_id?: string;
  payment_method: BillingReasonCode;
  external_ref?: string;
  notes?: string;
}

export interface BillingPayResponse {
  receipt_number: string;
  receipt_id?: string | null;
  visit_id: string;
  patient_id: string;
  cashier_pay_point_id?: string | null;
  total_paid_minor: number;
  currency: string;
  payment_method: BillingReasonCode;
  paid_item_ids: string[];
  paid_at: string;
  destination_hints: BillingPaymentDestinationHint[];
}

export interface BillingPaymentDestinationHint {
  billing_item_id: string;
  item_name: string;
  service_type: string;
  destination_label: string;
  assigned_dispensing_unit_id?: string | null;
  assigned_dispensing_unit_name?: string | null;
  readiness_state?: string | null;
}

export interface ReceiptSummary {
  id: string;
  clinic_id: string;
  patient_id: string;
  patient_name?: string | null;
  visit_id: string;
  cashier_pay_point_id?: string | null;
  receipt_number: string;
  total_amount_minor: number;
  currency: string;
  payment_method: BillingReasonCode;
  external_ref?: string | null;
  collected_by: string;
  collected_by_name?: string | null;
  occurred_at: string;
}

export interface ReceiptItemDetail {
  id: string;
  billing_item_id: string;
  amount_minor: number;
  item_name?: string | null;
  charge_code?: string | null;
}

export interface ReceiptDetail extends ReceiptSummary {
  notes?: string | null;
  items: ReceiptItemDetail[];
}

export interface ReceiptReprintResponse {
  receipt_id: string;
  receipt_number: string;
  reprint_log_id: string;
  reprinted_at: string;
}

export interface ReceiptSequence {
  clinic_id: string;
  prefix: string;
  padding: number;
  last_number: number;
  reset_yearly: boolean;
  current_year?: number | null;
}

export interface BillingRefundRequest {
  receipt_id: string;
  billing_item_id?: string;
  amount_minor?: number;
  reason: string;
  notes?: string;
}

export interface BillingRefundResponse {
  refund_id: string;
  receipt_id: string;
  amount_minor: number;
  currency: string;
  status: string;
  processed_at: string;
  refunded_item_ids: string[];
}

export interface PaymentMethodTotal {
  payment_method: BillingReasonCode;
  total_minor: number;
  count: number;
}

export interface DailyReport {
  date: string;
  clinic_id: string;
  total_collected_minor: number;
  total_refunded_minor: number;
  net_collected_minor: number;
  currency: string;
  receipts_count: number;
  refunds_count: number;
  method_breakdown: PaymentMethodTotal[];
}

export interface CashierShift {
  id: string;
  clinic_id: string;
  cashier_id: string;
  status: 'OPEN' | 'CLOSED';
  started_at: string;
  ended_at?: string | null;
  opening_float_minor: number;
  closing_cash_minor?: number | null;
  closing_note?: string | null;
}

export interface ShiftReport {
  shift: CashierShift;
  total_collected_minor: number;
  total_refunded_minor: number;
  net_collected_minor: number;
  receipts_count: number;
  refunds_count: number;
  method_breakdown: PaymentMethodTotal[];
}

export interface BillingTransactionRow {
  receipt_id: string;
  receipt_number: string;
  occurred_at: string;
  patient_name?: string | null;
  visit_id: string;
  amount_minor: number;
  currency: string;
  payment_method: BillingReasonCode;
  collected_by_name?: string | null;
}

export interface BillingTransactionsResponse {
  data: BillingTransactionRow[];
  total: number;
  page: number;
  limit: number;
  total_amount_minor: number;
  currency: string;
}

export interface CashierDashboardOverview {
  pending_charges_count: number;
  pharmacy_charges_pending: number;
  laboratory_charges_pending: number;
  paid_today_minor: number;
  receipts_today: number;
  active_queue: number;
  currency: string;
  last_updated_at: string;
}

export interface CashierDashboardChargeRow {
  billing_item_id: string;
  visit_id: string;
  patient_id: string;
  patient_name?: string | null;
  patient_mrn?: string | null;
  source_department_name?: string | null;
  item_name: string;
  quantity: number;
  amount_minor: number;
  currency: string;
  service_type: string;
  payment_status: string;
  cashier_pay_point_id?: string | null;
  cashier_pay_point_name?: string | null;
  assigned_dispensing_unit_id?: string | null;
  assigned_dispensing_unit_name?: string | null;
  pharmacy_readiness_state?: string | null;
  exception_authorization_type?: string | null;
  destination_hint?: string | null;
  created_at: string;
}

export interface CashierDashboardReceiptRow {
  receipt_id: string;
  receipt_number: string;
  visit_id: string;
  patient_id: string;
  patient_name?: string | null;
  patient_mrn?: string | null;
  amount_minor: number;
  currency: string;
  payment_method: BillingReasonCode;
  cashier_pay_point_id?: string | null;
  cashier_pay_point_name?: string | null;
  collected_by_name?: string | null;
  linked_items: string[];
  destination_hints: string[];
  occurred_at: string;
}

export interface CashierDashboardTransactionRow {
  receipt_id: string;
  receipt_number: string;
  visit_id: string;
  patient_id: string;
  patient_name?: string | null;
  patient_mrn?: string | null;
  amount_minor: number;
  currency: string;
  payment_method: BillingReasonCode;
  cashier_pay_point_id?: string | null;
  cashier_pay_point_name?: string | null;
  collected_by_name?: string | null;
  occurred_at: string;
}

export interface CashierDashboardExceptionHoldRow {
  prescription_id: string;
  billing_item_id?: string | null;
  patient_id: string;
  patient_name?: string | null;
  patient_mrn?: string | null;
  item_name: string;
  assigned_dispensing_unit_name?: string | null;
  exception_authorization_type: string;
  payment_status: string;
  readiness_state: string;
  cashier_pay_point_name?: string | null;
  occurred_at: string;
}

export interface CashierDashboardActivityRow {
  id: string;
  action_type: string;
  title: string;
  detail: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  receipt_number?: string | null;
  occurred_at: string;
}

export interface CashierDashboardResponse {
  overview: CashierDashboardOverview;
  pending_charges: CashierDashboardChargeRow[];
  pharmacy_charges: CashierDashboardChargeRow[];
  laboratory_charges: CashierDashboardChargeRow[];
  receipts: CashierDashboardReceiptRow[];
  transactions: CashierDashboardTransactionRow[];
  exceptions_holds: CashierDashboardExceptionHoldRow[];
  activity_audit: CashierDashboardActivityRow[];
}

export const billingWorkflowService = {
  getDashboardStreamUrl(params?: {
    search?: string;
    cashier_pay_point_id?: string;
    limit?: number;
  }): string {
    const baseUrl = String(client.defaults.baseURL || '').replace(/\/$/, '');
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.set('search', params.search);
    if (params?.cashier_pay_point_id) {
      searchParams.set('cashier_pay_point_id', params.cashier_pay_point_id);
    }
    if (params?.limit) searchParams.set('limit', String(params.limit));
    const query = searchParams.toString();
    return `${baseUrl}/v1/billing/dashboard-stream${query ? `?${query}` : ''}`;
  },

  async listChargeItems(serviceType?: 'LAB_TEST'): Promise<ChargeItemPrice[]> {
    const params = serviceType ? { service_type: serviceType } : undefined;
    const response = await client.get('/v1/billing/charge-items', { params });
    return response.data;
  },

  async listPending(params?: {
    search?: string;
    cashier_pay_point_id?: string;
  }): Promise<BillingPendingVisitSummary[]> {
    const response = await client.get('/v1/billing/pending', { params });
    return response.data;
  },

  async getDashboard(params?: {
    search?: string;
    cashier_pay_point_id?: string;
    limit?: number;
  }): Promise<CashierDashboardResponse> {
    const response = await client.get('/v1/billing/dashboard', { params });
    return response.data;
  },

  async listVisitItems(visitId: string): Promise<BillingItem[]> {
    const response = await client.get('/v1/billing/items', {
      params: { visit_id: visitId },
    });
    return response.data;
  },

  async pay(payload: BillingPayRequest): Promise<BillingPayResponse> {
    const response = await client.post('/v1/billing/pay', payload);
    return response.data;
  },

  async listReceipts(params?: {
    search?: string;
    date_from?: string;
    date_to?: string;
    limit?: number;
  }): Promise<ReceiptSummary[]> {
    const response = await client.get('/v1/billing/receipts', { params });
    return response.data;
  },

  async getReceiptDetail(receiptId: string): Promise<ReceiptDetail> {
    const response = await client.get(`/v1/billing/receipts/${receiptId}`);
    return response.data;
  },

  async reprintReceipt(receiptId: string, reason?: string): Promise<ReceiptReprintResponse> {
    const response = await client.post(`/v1/billing/receipts/${receiptId}/reprint`, {
      reason,
    });
    return response.data;
  },

  async getReceiptSequence(): Promise<ReceiptSequence> {
    const response = await client.get('/v1/billing/receipt-sequence');
    return response.data;
  },

  async updateReceiptSequence(payload: {
    prefix: string;
    padding: number;
    reset_yearly: boolean;
  }): Promise<ReceiptSequence> {
    const response = await client.put('/v1/billing/receipt-sequence', payload);
    return response.data;
  },

  async processRefund(payload: BillingRefundRequest): Promise<BillingRefundResponse> {
    const response = await client.post('/v1/billing/refunds', payload);
    return response.data;
  },

  async getDailyReport(forDate?: string): Promise<DailyReport> {
    const params = forDate ? { for_date: forDate } : undefined;
    const response = await client.get('/v1/billing/daily-report', { params });
    return response.data;
  },

  async startShift(openingFloatMinor = 0): Promise<CashierShift> {
    const response = await client.post('/v1/billing/shifts/start', {
      opening_float_minor: openingFloatMinor,
    });
    return response.data;
  },

  async endShift(payload?: {
    closing_cash_minor?: number;
    closing_note?: string;
  }): Promise<CashierShift> {
    const response = await client.post('/v1/billing/shifts/end', payload || {});
    return response.data;
  },

  async getCurrentShift(): Promise<CashierShift | null> {
    const response = await client.get('/v1/billing/shifts/current');
    return response.data;
  },

  async getShiftReport(shiftId: string): Promise<ShiftReport> {
    const response = await client.get(`/v1/billing/shifts/${shiftId}/report`);
    return response.data;
  },

  async listTransactions(params?: {
    start_date?: string;
    end_date?: string;
    payment_method?: BillingReasonCode;
    search?: string;
    page?: number;
    limit?: number;
  }): Promise<BillingTransactionsResponse> {
    const response = await client.get('/v1/billing/transactions', { params });
    return response.data;
  },
};
