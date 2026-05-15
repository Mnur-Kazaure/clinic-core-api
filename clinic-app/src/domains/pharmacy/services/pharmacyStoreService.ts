import client from '@/api/client';

export type PharmacyStoreSeverity = 'info' | 'warning' | 'critical';
export type PharmacyStoreRequestStatus =
  | 'PENDING'
  | 'AWAITING_CMD_APPROVAL'
  | 'APPROVED'
  | 'ISSUE_PREPARATION_IN_PROGRESS'
  | 'REJECTED'
  | 'BACKORDERED'
  | 'BACKORDER_PENDING'
  | 'PARTIALLY_ISSUED'
  | 'ISSUED'
  | 'DISPATCHED'
  | 'PARTIALLY_RECEIVED'
  | 'ACKNOWLEDGED'
  | 'RECEIVED'
  | 'CLOSED'
  | 'CANCELLED';
export type PharmacyStoreIssueVoucherStatus =
  | 'DRAFT'
  | 'PREPARED'
  | 'ISSUED'
  | 'DISPATCHED'
  | 'ACKNOWLEDGED'
  | 'CLOSED'
  | 'PARTIALLY_RECEIVED'
  | 'RECEIVED'
  | 'CANCELLED';
export type PharmacyStoreRequestPriority = 'ROUTINE' | 'URGENT' | 'EMERGENCY';
export type PharmacyStoreRiskLevel = 'LOW_STOCK' | 'EXPIRING_SOON' | 'EXPIRED';
export type PharmacyStoreRequestType =
  | 'PHARMACY_REFILL'
  | 'DEPARTMENT_COMMODITY'
  | 'EMERGENCY_REQUEST'
  | 'EQUIPMENT_REQUEST';
export type PharmacyStoreInventoryClassification = 'DRUG' | 'CONSUMABLE' | 'EQUIPMENT';
export type PharmacyStoreInventoryTrackingMode = 'LOT_TRACKED' | 'QUANTITY_ONLY' | 'SERIALIZED';
export type PharmacyStoreReturnRequestStatus =
  | 'RETURN_REQUESTED'
  | 'RETURN_PENDING_STORE_REVIEW'
  | 'RETURN_ACCEPTED'
  | 'RETURN_REJECTED'
  | 'RETURN_RECEIVED'
  | 'RETURN_CLOSED';
export type PharmacyStoreReturnReasonCode =
  | 'EXCESS_UNUSED'
  | 'WRONG_ISSUE'
  | 'DAMAGED_ON_RECEIPT'
  | 'EXPIRED_AT_UNIT'
  | 'UNIT_TRANSFER_CORRECTION'
  | 'OTHER';

export interface PharmacyStoreOverview {
  pending_approved_requests: number;
  items_awaiting_issue: number;
  pending_receiving_acknowledgements: number;
  pending_return_reviews: number;
  low_stock_items: number;
  expiring_soon_items: number;
  stock_adjustments_pending: number;
  currency: string;
  last_updated_at: string;
}

export interface PharmacyStoreOperationalSummaryRow {
  label: string;
  count: number;
  detail?: string | null;
  severity: PharmacyStoreSeverity;
}

export interface PharmacyStoreInventoryRow {
  inventory_item_id: string;
  item_name: string;
  dosage_form: string;
  strength?: string | null;
  classification: PharmacyStoreInventoryClassification;
  tracking_mode: PharmacyStoreInventoryTrackingMode;
  requires_expiry: boolean;
  category: string;
  unit_of_measure: string;
  batch_number?: string | null;
  expiry_date?: string | null;
  quantity_on_hand: number;
  reserved_quantity: number;
  available_quantity: number;
  low_stock_threshold: number;
  stock_status: string;
  currency: string;
  location_label?: string | null;
  can_issue: boolean;
}

export interface PharmacyStoreRequestItemRow {
  refill_request_item_id: string;
  inventory_item_id: string;
  inventory_item_name: string;
  requested_quantity: number;
  approved_quantity: number;
  reserved_quantity: number;
  issued_quantity: number;
  received_quantity: number;
  pending_quantity: number;
  backorder_quantity: number;
}

export interface PharmacyStoreApprovedRequestRow {
  request_id: string;
  request_number: string;
  requesting_unit_id: string;
  requesting_unit_name: string;
  request_type: PharmacyStoreRequestType;
  requested_at: string;
  approved_by_name?: string | null;
  priority: PharmacyStoreRequestPriority;
  status: PharmacyStoreRequestStatus;
  item_count: number;
  total_requested_quantity: number;
  total_reserved_quantity: number;
  total_pending_quantity: number;
  backorder_pending: boolean;
  waiting_minutes: number;
  requester_timeline: string[];
  items: PharmacyStoreRequestItemRow[];
}

export interface PharmacyStoreIssueVoucherItemRow {
  voucher_item_id: string;
  inventory_item_id: string;
  inventory_item_name: string;
  requested_quantity: number;
  reserved_quantity: number;
  issued_quantity: number;
  received_quantity: number;
  pending_quantity: number;
  batch_number: string;
  expiry_date?: string | null;
}

export interface PharmacyStoreIssueVoucherRow {
  voucher_id: string;
  voucher_number: string;
  receiving_unit_id: string;
  receiving_unit_name: string;
  issue_date?: string | null;
  prepared_at?: string | null;
  dispatched_at?: string | null;
  prepared_by_name?: string | null;
  issued_by_name?: string | null;
  approved_by_name?: string | null;
  received_by_name?: string | null;
  status: PharmacyStoreIssueVoucherStatus;
  partial_issue: boolean;
  pending_quantity: number;
  awaiting_acknowledgement: boolean;
  discrepancy_pending: boolean;
  items: PharmacyStoreIssueVoucherItemRow[];
}

export interface PharmacyStoreReturnRequestRow {
  id: string;
  return_number: string;
  clinic_id: string;
  issue_voucher_id: string;
  issue_voucher_number: string;
  issue_voucher_item_id: string;
  refill_request_id?: string | null;
  returning_unit_id: string;
  returning_unit_name: string;
  store_unit_id: string;
  store_unit_name: string;
  inventory_item_id: string;
  inventory_item_name: string;
  batch_number: string;
  expiry_date?: string | null;
  original_issued_quantity: number;
  quantity_already_returned: number;
  quantity_now_returned: number;
  quantity_received: number;
  remaining_issued_balance: number;
  eligible_return_quantity: number;
  reason_code: PharmacyStoreReturnReasonCode;
  reason_note?: string | null;
  status: PharmacyStoreReturnRequestStatus;
  requested_by: string;
  requested_by_name?: string | null;
  requested_at: string;
  reviewed_by?: string | null;
  reviewed_by_name?: string | null;
  reviewed_at?: string | null;
  review_note?: string | null;
  received_by?: string | null;
  received_by_name?: string | null;
  received_at?: string | null;
  receive_note?: string | null;
  closed_at?: string | null;
  return_timeline: string[];
}

export interface PharmacyStoreMovementRow {
  movement_id: string;
  occurred_at: string;
  movement_type: string;
  item_name: string;
  batch_number?: string | null;
  quantity_delta: number;
  source_label?: string | null;
  destination_label?: string | null;
  actor_name?: string | null;
  reference_number?: string | null;
  reference_type?: string | null;
}

export interface PharmacyStoreExpiryRow {
  inventory_item_id: string;
  item_name: string;
  batch_number: string;
  expiry_date?: string | null;
  quantity_on_hand: number;
  risk_level: PharmacyStoreRiskLevel;
  recommended_action: string;
}

export interface PharmacyStoreAdjustmentRow {
  movement_id: string;
  occurred_at: string;
  item_name: string;
  batch_number?: string | null;
  quantity_delta: number;
  actor_name?: string | null;
  reason?: string | null;
  reference_number?: string | null;
}

export interface PharmacyStoreActivityRow {
  id: string;
  occurred_at: string;
  action_type: string;
  summary: string;
  detail?: string | null;
  item_name?: string | null;
  unit_name?: string | null;
  voucher_number?: string | null;
  request_number?: string | null;
  actor_name?: string | null;
  severity: PharmacyStoreSeverity;
}

export interface PharmacyStoreTrendRow {
  label: string;
  value: number;
}

export interface PharmacyStoreReportsAnalytics {
  stock_received_by_period: number;
  stock_issued_by_period: number;
  issue_volume_by_unit: PharmacyStoreTrendRow[];
  top_consumed_items: PharmacyStoreTrendRow[];
  stock_out_frequency: PharmacyStoreTrendRow[];
  expiry_trend: PharmacyStoreTrendRow[];
  backorder_trend: PharmacyStoreTrendRow[];
  adjustment_trend: PharmacyStoreTrendRow[];
}

export interface PharmacyStoreDashboardResponse {
  generated_at: string;
  start_date: string;
  end_date: string;
  store_unit_id: string;
  store_unit_name: string;
  currency: string;
  overview: PharmacyStoreOverview;
  supply_workload: PharmacyStoreOperationalSummaryRow[];
  stock_risk_summary: PharmacyStoreOperationalSummaryRow[];
  dispatch_status: PharmacyStoreOperationalSummaryRow[];
  top_consuming_units: PharmacyStoreTrendRow[];
  inventory: PharmacyStoreInventoryRow[];
  department_requests: PharmacyStoreApprovedRequestRow[];
  approved_requests: PharmacyStoreApprovedRequestRow[];
  issue_vouchers: PharmacyStoreIssueVoucherRow[];
  dispatch_receiving: PharmacyStoreIssueVoucherRow[];
  return_requests: PharmacyStoreReturnRequestRow[];
  movement_history: PharmacyStoreMovementRow[];
  expiry_low_stock: PharmacyStoreExpiryRow[];
  adjustments_reconciliation: PharmacyStoreAdjustmentRow[];
  activity_audit: PharmacyStoreActivityRow[];
  reports_analytics: PharmacyStoreReportsAnalytics;
}

export interface PharmacyStoreReceiveStockPayload {
  store_unit_id: string;
  inventory_item_id: string;
  batch_number: string;
  expiry_date?: string | null;
  quantity_received: number;
  unit_cost_minor?: number | null;
  source_reference_note?: string | null;
}

export interface PharmacyStoreAdjustmentPayload {
  store_unit_id: string;
  inventory_item_id: string;
  batch_number?: string | null;
  expiry_date?: string | null;
  quantity_delta: number;
  reason: string;
}

export interface PharmacyStoreIssueVoucherCreatePayload {
  refill_request_id: string;
  store_unit_id: string;
  note?: string | null;
  items: Array<{
    refill_request_item_id: string;
    batch_number: string;
    expiry_date?: string | null;
    issued_quantity: number;
  }>;
}

export interface PharmacyStoreStockActionResponse {
  inventory_item_id: string;
  item_name: string;
  batch_number?: string | null;
  quantity_on_hand: number;
  stock_quantity: number;
  reference_number: string;
  occurred_at: string;
}

export interface PharmacyStoreIssueVoucherDispatchPayload {
  note?: string | null;
}

export interface PharmacyStoreReturnReviewPayload {
  decision: 'ACCEPT' | 'REJECT';
  review_note?: string | null;
}

export interface PharmacyStoreReturnReceivePayload {
  receive_note?: string | null;
}

export const pharmacyStoreService = {
  getDashboardStreamUrl(params?: {
    start_date?: string;
    end_date?: string;
    store_unit_id?: string;
  }): string {
    const baseUrl = String(client.defaults.baseURL || '').replace(/\/$/, '');
    const searchParams = new URLSearchParams();
    if (params?.start_date) searchParams.set('start_date', params.start_date);
    if (params?.end_date) searchParams.set('end_date', params.end_date);
    if (params?.store_unit_id) searchParams.set('store_unit_id', params.store_unit_id);
    const query = searchParams.toString();
    return `${baseUrl}/v1/pharmacy-store/dashboard-stream${query ? `?${query}` : ''}`;
  },

  async getDashboard(params?: {
    start_date?: string;
    end_date?: string;
    store_unit_id?: string;
  }): Promise<PharmacyStoreDashboardResponse> {
    const response = await client.get('/v1/pharmacy-store/dashboard', { params });
    return response.data;
  },

  async receiveStock(
    payload: PharmacyStoreReceiveStockPayload
  ): Promise<PharmacyStoreStockActionResponse> {
    const response = await client.post('/v1/pharmacy-store/receive-stock', payload);
    return response.data;
  },

  async createAdjustment(
    payload: PharmacyStoreAdjustmentPayload
  ): Promise<PharmacyStoreStockActionResponse> {
    const response = await client.post('/v1/pharmacy-store/adjustments', payload);
    return response.data;
  },

  async createIssueVoucher(
    payload: PharmacyStoreIssueVoucherCreatePayload
  ): Promise<PharmacyStoreIssueVoucherRow> {
    const response = await client.post('/v1/pharmacy-store/issue-vouchers', payload);
    return response.data;
  },

  async dispatchIssueVoucher(
    voucherId: string,
    payload: PharmacyStoreIssueVoucherDispatchPayload
  ): Promise<PharmacyStoreIssueVoucherRow> {
    const response = await client.post(
      `/v1/pharmacy-store/issue-vouchers/${voucherId}/dispatch`,
      payload
    );
    return response.data;
  },

  async reviewReturnRequest(
    returnRequestId: string,
    payload: PharmacyStoreReturnReviewPayload
  ): Promise<PharmacyStoreReturnRequestRow> {
    const response = await client.post(
      `/v1/pharmacy-store/return-requests/${returnRequestId}/review`,
      payload
    );
    return response.data;
  },

  async receiveReturnRequest(
    returnRequestId: string,
    payload: PharmacyStoreReturnReceivePayload
  ): Promise<PharmacyStoreReturnRequestRow> {
    const response = await client.post(
      `/v1/pharmacy-store/return-requests/${returnRequestId}/receive`,
      payload
    );
    return response.data;
  },
};
