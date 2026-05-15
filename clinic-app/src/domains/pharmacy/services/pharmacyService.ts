import client from '@/api/client';
import {
  PharmacyExceptionAuthorizationType,
  PharmacyPrescriptionWorkflowStatus,
  PrescriptionFulfillmentType,
  PrescriptionStatus,
} from '@/shared/enums';
import { PrescriptionResponse } from '@/shared/types';

export type PharmacyDispensingPriority = 'ROUTINE' | 'URGENT' | 'EMERGENCY';
export type PharmacyDispensingSeverity = 'info' | 'warning' | 'critical';
export type PharmacyDispensingStockStatus =
  | 'IN_STOCK'
  | 'LOW_STOCK'
  | 'OUT_OF_STOCK'
  | 'EXPIRED'
  | 'UNMAPPED';
export type PharmacyRefillRequestStatus =
  | 'PENDING'
  | 'AWAITING_CMD_APPROVAL'
  | 'APPROVED'
  | 'ISSUE_PREPARATION_IN_PROGRESS'
  | 'REJECTED'
  | 'BACKORDERED'
  | 'BACKORDER_PENDING'
  | 'PARTIALLY_ISSUED'
  | 'DISPATCHED'
  | 'PARTIALLY_RECEIVED'
  | 'ACKNOWLEDGED'
  | 'RECEIVED'
  | 'CLOSED'
  | 'CANCELLED';
export type PharmacyIssueVoucherStatus =
  | 'DRAFT'
  | 'PREPARED'
  | 'ISSUED'
  | 'DISPATCHED'
  | 'ACKNOWLEDGED'
  | 'CLOSED'
  | 'PARTIALLY_RECEIVED'
  | 'RECEIVED'
  | 'CANCELLED';
export type PharmacyRequestType =
  | 'PHARMACY_REFILL'
  | 'DEPARTMENT_COMMODITY'
  | 'EMERGENCY_REQUEST'
  | 'EQUIPMENT_REQUEST';
export type PharmacyReturnRequestStatus =
  | 'RETURN_REQUESTED'
  | 'RETURN_PENDING_STORE_REVIEW'
  | 'RETURN_ACCEPTED'
  | 'RETURN_REJECTED'
  | 'RETURN_RECEIVED'
  | 'RETURN_CLOSED';
export type PharmacyReturnReasonCode =
  | 'EXCESS_UNUSED'
  | 'WRONG_ISSUE'
  | 'DAMAGED_ON_RECEIPT'
  | 'EXPIRED_AT_UNIT'
  | 'UNIT_TRANSFER_CORRECTION'
  | 'OTHER';

export interface DispenseCreateRequest {
  pharmacist_id: string;
  quantity: number;
  unit_id?: string;
  stock_lot_id?: string;
}

export interface DispenseResponse {
  id: string;
  prescription_id: string;
  pharmacist_id: string;
  quantity: number;
  quantity_dispensed_total: number;
  quantity_remaining: number;
  workflow_status: PharmacyPrescriptionWorkflowStatus;
  dispensed_at: string;
}

export interface ExternalFulfillCreateRequest {
  note: string;
}

export interface PrescriptionFulfillmentResponse {
  id: string;
  clinic_id: string;
  prescription_id: string;
  actor_id: string;
  fulfillment_type: PrescriptionFulfillmentType;
  quantity: number | null;
  note: string | null;
  occurred_at: string;
}

export interface DispensingReassignmentCreateRequest {
  target_unit_id: string;
  reason: string;
  note?: string;
}

export interface DispensingReassignmentResponse {
  prescription_id: string;
  previous_unit_id?: string | null;
  target_unit_id: string;
  workflow_status: string;
  reason: string;
  note?: string | null;
}

export interface PharmacyRefillRequestItemResponse {
  id: string;
  inventory_item_id: string;
  inventory_item_name: string;
  requested_quantity: number;
  approved_quantity?: number | null;
  reserved_quantity: number;
  issued_quantity: number;
  received_quantity: number;
  note?: string | null;
}

export interface PharmacyRefillRequestResponse {
  id: string;
  clinic_id: string;
  requesting_unit_id: string;
  requesting_unit_name: string;
  requested_by: string;
  requested_by_name?: string | null;
  request_type: PharmacyRequestType;
  status: PharmacyRefillRequestStatus;
  urgency?: string | null;
  note?: string | null;
  reviewed_by?: string | null;
  reviewed_by_name?: string | null;
  reviewed_at?: string | null;
  review_note?: string | null;
  hod_visible_at?: string | null;
  requested_at: string;
  requester_timeline: string[];
  items: PharmacyRefillRequestItemResponse[];
}

export interface PharmacyIssueVoucherItemResponse {
  id: string;
  inventory_item_id: string;
  inventory_item_name: string;
  refill_request_item_id?: string | null;
  batch_number: string;
  expiry_date?: string | null;
  issued_quantity: number;
  received_quantity: number;
}

export interface PharmacyIssueVoucherResponse {
  id: string;
  clinic_id: string;
  voucher_number: string;
  store_unit_id: string;
  store_unit_name: string;
  receiving_unit_id: string;
  receiving_unit_name: string;
  refill_request_id?: string | null;
  status: PharmacyIssueVoucherStatus;
  prepared_by?: string | null;
  prepared_by_name?: string | null;
  prepared_at?: string | null;
  approved_by?: string | null;
  approved_by_name?: string | null;
  issued_by?: string | null;
  issued_by_name?: string | null;
  issued_at?: string | null;
  dispatched_by?: string | null;
  dispatched_at?: string | null;
  acknowledged_by?: string | null;
  acknowledged_by_name?: string | null;
  acknowledged_at?: string | null;
  closed_at?: string | null;
  note?: string | null;
  items: PharmacyIssueVoucherItemResponse[];
}

export interface PharmacyReturnRequestResponse {
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
  reason_code: PharmacyReturnReasonCode;
  reason_note?: string | null;
  status: PharmacyReturnRequestStatus;
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

export interface PharmacyDispensingOverview {
  assigned_prescriptions: number;
  ready_to_dispense: number;
  awaiting_payment_clearance: number;
  reassigned: number;
  out_of_stock: number;
  completed_today: number;
  last_updated_at: string;
}

export interface PharmacyDispensingNextAction {
  severity: PharmacyDispensingSeverity;
  title: string;
  detail: string;
}

export interface PharmacyDispensingReassignmentTarget {
  unit_id: string;
  unit_name: string;
}

export interface PharmacyDispensingQueueRow {
  prescription_id: string;
  visit_id: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  source_department_name?: string | null;
  item_name: string;
  dosage: string;
  frequency: string;
  duration: string;
  instructions?: string | null;
  quantity_prescribed: number;
  quantity_dispensed_total: number;
  quantity_remaining: number;
  readiness_state: PharmacyPrescriptionWorkflowStatus;
  payment_state: string;
  assigned_unit_id?: string | null;
  assigned_unit_name?: string | null;
  cashier_pay_point_name?: string | null;
  priority: PharmacyDispensingPriority;
  aging_minutes: number;
  exception_authorization_type: PharmacyExceptionAuthorizationType;
  local_stock_status: PharmacyDispensingStockStatus;
  local_stock_available_quantity: number;
  prescribed_by_name?: string | null;
  dispensed_by_name?: string | null;
  issued_at: string;
  dispensed_at?: string | null;
  recently_reassigned: boolean;
  last_reassignment_at?: string | null;
  reassignment_reason?: string | null;
  reassignment_note?: string | null;
}

export interface PharmacyDispensingLocalStockRow {
  inventory_item_id: string;
  item_name: string;
  batch_number: string;
  expiry_date?: string | null;
  quantity_on_hand: number;
  low_stock_threshold: number;
  stock_status: Exclude<PharmacyDispensingStockStatus, 'UNMAPPED'>;
  blocked: boolean;
  source_label: string;
}

export interface PharmacyDispensingAlertRow {
  id: string;
  severity: PharmacyDispensingSeverity;
  alert_type: string;
  title: string;
  detail: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  item_name?: string | null;
  occurred_at: string;
}

export interface PharmacyDispensingActivityRow {
  id: string;
  occurred_at: string;
  action_type: string;
  summary: string;
  detail?: string | null;
  actor_name?: string | null;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  item_name?: string | null;
  severity: PharmacyDispensingSeverity;
}

export interface PharmacyDispensingDashboardResponse {
  generated_at: string;
  unit_id: string;
  unit_name: string;
  overview: PharmacyDispensingOverview;
  next_action?: PharmacyDispensingNextAction | null;
  reassignment_targets: PharmacyDispensingReassignmentTarget[];
  prescriptions: PharmacyDispensingQueueRow[];
  local_stock: PharmacyDispensingLocalStockRow[];
  refill_requests: PharmacyRefillRequestResponse[];
  issue_vouchers: PharmacyIssueVoucherResponse[];
  return_requests: PharmacyReturnRequestResponse[];
  alerts: PharmacyDispensingAlertRow[];
  activity_audit: PharmacyDispensingActivityRow[];
}

export interface PharmacyRefillRequestCreatePayload {
  unit_id?: string;
  request_type?: PharmacyRequestType;
  urgency?: string | null;
  note?: string | null;
  items: Array<{
    inventory_item_id: string;
    requested_quantity: number;
    note?: string | null;
  }>;
}

export interface PharmacyIssueVoucherAcknowledgePayload {
  unit_id?: string;
  note?: string | null;
  items: Array<{
    voucher_item_id: string;
    received_quantity: number;
  }>;
}

export interface PharmacyReturnRequestCreatePayload {
  unit_id?: string;
  issue_voucher_id: string;
  issue_voucher_item_id: string;
  quantity_now_returned: number;
  reason_code: PharmacyReturnReasonCode;
  reason_note?: string | null;
}

export const pharmacyService = {
  getDashboardStreamUrl(params?: { unit_id?: string }): string {
    const baseUrl = String(client.defaults.baseURL || '').replace(/\/$/, '');
    const searchParams = new URLSearchParams();
    if (params?.unit_id) searchParams.set('unit_id', params.unit_id);
    const query = searchParams.toString();
    return `${baseUrl}/v1/pharmacy/dashboard-stream${query ? `?${query}` : ''}`;
  },

  async getDashboard(params?: {
    unit_id?: string;
  }): Promise<PharmacyDispensingDashboardResponse> {
    const response = await client.get('/v1/pharmacy/dashboard', { params });
    return response.data;
  },

  async getPrescriptions(
    params?: {
      status?: PrescriptionStatus;
      workflow_status?: PharmacyPrescriptionWorkflowStatus;
      unit_id?: string;
    }
  ): Promise<PrescriptionResponse[]> {
    const response = await client.get('/v1/pharmacy/prescriptions', { params });
    return response.data;
  },

  async getPrescription(
    prescriptionId: string,
    unitId?: string
  ): Promise<PrescriptionResponse> {
    const response = await client.get(
      `/v1/pharmacy/prescriptions/${prescriptionId}`,
      { params: unitId ? { unit_id: unitId } : undefined }
    );
    return response.data;
  },

  async dispensePrescription(
    prescriptionId: string,
    payload: DispenseCreateRequest
  ): Promise<DispenseResponse> {
    const response = await client.post(
      `/v1/pharmacy/prescriptions/${prescriptionId}/dispense`,
      payload
    );
    return response.data;
  },

  async fulfillPrescriptionExternal(
    prescriptionId: string,
    payload: ExternalFulfillCreateRequest
  ): Promise<PrescriptionFulfillmentResponse> {
    const response = await client.post(
      `/v1/pharmacy/prescriptions/${prescriptionId}/fulfill-external`,
      payload
    );
    return response.data;
  },

  async reassignPrescription(
    prescriptionId: string,
    payload: DispensingReassignmentCreateRequest
  ): Promise<DispensingReassignmentResponse> {
    const response = await client.post(
      `/v1/pharmacy/prescriptions/${prescriptionId}/reassign`,
      payload
    );
    return response.data;
  },

  async getRefillRequests(params?: { unit_id?: string }): Promise<PharmacyRefillRequestResponse[]> {
    const response = await client.get('/v1/pharmacy/refill-requests', { params });
    return response.data;
  },

  async createRefillRequest(
    payload: PharmacyRefillRequestCreatePayload
  ): Promise<PharmacyRefillRequestResponse> {
    const response = await client.post('/v1/pharmacy/refill-requests', payload);
    return response.data;
  },

  async getIssueVouchers(params?: { unit_id?: string }): Promise<PharmacyIssueVoucherResponse[]> {
    const response = await client.get('/v1/pharmacy/issue-vouchers', { params });
    return response.data;
  },

  async acknowledgeIssueVoucher(
    voucherId: string,
    payload: PharmacyIssueVoucherAcknowledgePayload
  ): Promise<PharmacyIssueVoucherResponse> {
    const response = await client.post(
      `/v1/pharmacy/issue-vouchers/${voucherId}/acknowledge`,
      payload
    );
    return response.data;
  },

  async createReturnRequest(
    payload: PharmacyReturnRequestCreatePayload
  ): Promise<PharmacyReturnRequestResponse> {
    const response = await client.post('/v1/pharmacy/return-requests', payload);
    return response.data;
  },
};
