import client from '@/api/client';
import {
  PharmacyExceptionAuthorizationType,
  PharmacyPrescriptionWorkflowStatus,
  UserRole,
} from '@/shared/enums';
import type { PharmacyCatalogRegistryRow } from './pharmacyCatalogGovernanceService';

export type PharmacyHodUnitCategory = 'STORE' | 'DISPENSING' | 'SATELLITE';
export type PharmacyHodRefillRequestStatus =
  | 'PENDING'
  | 'AWAITING_CMD_APPROVAL'
  | 'APPROVED'
  | 'ISSUE_PREPARATION_IN_PROGRESS'
  | 'REJECTED'
  | 'PARTIALLY_ISSUED'
  | 'BACKORDER_PENDING'
  | 'ISSUED'
  | 'DISPATCHED'
  | 'PARTIALLY_RECEIVED'
  | 'ACKNOWLEDGED'
  | 'RECEIVED'
  | 'CLOSED'
  | 'CANCELLED';
export type PharmacyHodIssueVoucherStatus =
  | 'DRAFT'
  | 'PREPARED'
  | 'ISSUED'
  | 'DISPATCHED'
  | 'ACKNOWLEDGED'
  | 'CLOSED'
  | 'PARTIALLY_RECEIVED'
  | 'RECEIVED'
  | 'CANCELLED';

export interface PharmacyHodOverviewMetric {
  pending_prescriptions: number;
  ready_to_dispense: number;
  awaiting_payment_clearance: number;
  stock_risk_items: number;
  pending_refill_requests: number;
  critical_alerts: number;
  delayed_dispense_count: number;
  currency: string;
  last_updated_at: string;
}

export interface PharmacyHodSystemHealth {
  key: string;
  label: string;
  status: 'OK' | 'ATTENTION';
  detail: string;
}

export interface PharmacyHodUnitSummary {
  unit_id: string;
  unit_name: string;
  category: PharmacyHodUnitCategory;
  queue_volume: number;
  ready_to_dispense: number;
  awaiting_payment_clearance: number;
  stock_risk: number;
  revenue_today_minor: number;
}

export interface PharmacyHodPayPointPerformance {
  pay_point_id: string;
  pay_point_name: string;
  transaction_count: number;
  revenue_minor: number;
  awaiting_clearance_count: number;
  currency: string;
}

export interface PharmacyHodBottleneckItem {
  severity: 'info' | 'warning' | 'critical';
  title: string;
  detail: string;
  unit_id?: string | null;
  unit_name?: string | null;
}

export interface PharmacyHodUnitOperation {
  unit_id: string;
  unit_name: string;
  category: PharmacyHodUnitCategory;
  queue_volume: number;
  ready_to_dispense: number;
  awaiting_payment_clearance: number;
  staff_on_duty: number;
  stock_status: string;
  average_dispense_time_minutes?: number | null;
  bottlenecks: string[];
}

export interface PharmacyHodDispensingOversightRow {
  prescription_id: string;
  visit_id: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  unit_id?: string | null;
  unit_name?: string | null;
  item_name: string;
  readiness_state: PharmacyPrescriptionWorkflowStatus;
  payment_state: string;
  assigned_staff_id?: string | null;
  assigned_staff_name?: string | null;
  delay_minutes: number;
  exception_authorization_type: PharmacyExceptionAuthorizationType;
  issued_at: string;
  resolved_at?: string | null;
}

export interface PharmacyHodRefillRequestRow {
  request_id: string;
  requesting_unit_id: string;
  requesting_unit_name: string;
  requested_by_id: string;
  requested_by_name?: string | null;
  status: PharmacyHodRefillRequestStatus;
  urgency?: string | null;
  requested_at: string;
  item_count: number;
  total_requested_quantity: number;
  total_approved_quantity: number;
}

export interface PharmacyHodIssueVoucherRow {
  voucher_id: string;
  voucher_number: string;
  store_unit_id: string;
  store_unit_name: string;
  receiving_unit_id: string;
  receiving_unit_name: string;
  status: PharmacyHodIssueVoucherStatus;
  approved_by_name?: string | null;
  issued_by_name?: string | null;
  acknowledged_by_name?: string | null;
  issued_at: string;
  acknowledged_at?: string | null;
  partial_issue: boolean;
  backorder_pending: boolean;
  item_count: number;
}

export interface PharmacyHodUnitContext {
  id: string;
  name: string;
  category: PharmacyHodUnitCategory;
}

export interface PharmacyHodStaffSummary {
  user_id: string;
  full_name?: string | null;
  email: string;
  role: UserRole;
  is_active: boolean;
  assigned_units: PharmacyHodUnitContext[];
  default_unit_id?: string | null;
  default_unit_name?: string | null;
  recent_activity_summary?: string | null;
  recent_activity_at?: string | null;
}

export interface PharmacyHodUnitAssignmentMember {
  user_id: string;
  full_name?: string | null;
  role: UserRole;
  is_default: boolean;
  is_active: boolean;
}

export interface PharmacyHodUnitAssignment {
  unit_id: string;
  unit_name: string;
  category: PharmacyHodUnitCategory;
  members: PharmacyHodUnitAssignmentMember[];
}

export interface PharmacyHodExceptionOversightRow {
  prescription_id: string;
  visit_id: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  unit_id?: string | null;
  unit_name?: string | null;
  exception_type: PharmacyExceptionAuthorizationType;
  authorized_by_id?: string | null;
  authorized_by_name?: string | null;
  authorized_at?: string | null;
  workflow_status: PharmacyPrescriptionWorkflowStatus;
  resolution_status: string;
}

export interface PharmacyHodCriticalAlertRow {
  alert_type: string;
  severity: 'warning' | 'critical';
  title: string;
  detail: string;
  unit_id?: string | null;
  unit_name?: string | null;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  occurred_at: string;
}

export interface PharmacyHodStockRiskRow {
  unit_id?: string | null;
  unit_name: string;
  item_id: string;
  item_name: string;
  quantity_on_hand: number;
  low_stock_threshold: number;
  earliest_expiry_date?: string | null;
  risk_level: 'LOW' | 'CRITICAL' | 'EXPIRING_SOON' | 'EXPIRED';
  detail: string;
}

export interface PharmacyHodActivityAuditRow {
  id: string;
  source_type: string;
  action_type: string;
  occurred_at: string;
  actor_id?: string | null;
  actor_name?: string | null;
  actor_role?: string | null;
  unit_id?: string | null;
  unit_name?: string | null;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  receipt_number?: string | null;
  summary: string;
  detail?: string | null;
  severity: 'info' | 'warning' | 'critical';
}

export interface PharmacyHodStaffPerformance {
  user_id: string;
  full_name?: string | null;
  role: UserRole;
  assigned_units: string[];
  prescriptions_handled: number;
  average_dispense_time_minutes?: number | null;
  pending_load: number;
  reassignment_count: number;
  stock_issue_events: number;
  shift_activity_count: number;
}

export interface PharmacyHodSalesRevenueByUnit {
  unit_id?: string | null;
  unit_name: string;
  revenue_minor: number;
}

export interface PharmacyHodSalesRevenueRow {
  receipt_id: string;
  receipt_number: string;
  occurred_at: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  visit_id: string;
  item_name: string;
  unit_id?: string | null;
  unit_name?: string | null;
  cashier_pay_point_id?: string | null;
  cashier_pay_point_name?: string | null;
  amount_minor: number;
  currency: string;
  cashier_name?: string | null;
}

export interface PharmacyHodSalesRevenue {
  total_revenue_minor: number;
  receipt_count: number;
  paid_item_count: number;
  currency: string;
  revenue_by_unit: PharmacyHodSalesRevenueByUnit[];
  rows: PharmacyHodSalesRevenueRow[];
}

export interface PharmacyHodReceiptRegisterRow {
  receipt_id: string;
  receipt_number: string;
  occurred_at: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  visit_id: string;
  amount_minor: number;
  currency: string;
  cashier_name?: string | null;
  cashier_pay_point_name?: string | null;
  unit_names: string[];
  linked_items: string[];
}

export interface PharmacyHodReportsAnalytics {
  revenue_by_unit: PharmacyHodSalesRevenueByUnit[];
  revenue_by_pay_point: PharmacyHodPayPointPerformance[];
  refill_frequency_by_unit: PharmacyHodSalesRevenueByUnit[];
  dispense_turnaround_by_unit: PharmacyHodSalesRevenueByUnit[];
  stock_risk_counts: Array<{ label: string; count: number }>;
}

export interface PharmacyHodDashboardResponse {
  generated_at: string;
  start_date: string;
  end_date: string;
  overview: PharmacyHodOverviewMetric;
  system_health: PharmacyHodSystemHealth[];
  unit_summary: PharmacyHodUnitSummary[];
  pay_point_performance: PharmacyHodPayPointPerformance[];
  bottlenecks: PharmacyHodBottleneckItem[];
  unit_operations: PharmacyHodUnitOperation[];
  dispensing_oversight: PharmacyHodDispensingOversightRow[];
  store_supply: PharmacyHodRefillRequestRow[];
  issue_vouchers: PharmacyHodIssueVoucherRow[];
  staff_control: PharmacyHodStaffSummary[];
  unit_assignment: PharmacyHodUnitAssignment[];
  pending_approvals: PharmacyHodRefillRequestRow[];
  exception_oversight: PharmacyHodExceptionOversightRow[];
  critical_alerts: PharmacyHodCriticalAlertRow[];
  stock_risk_expiry: PharmacyHodStockRiskRow[];
  activity_audit: PharmacyHodActivityAuditRow[];
  staff_performance: PharmacyHodStaffPerformance[];
  sales_revenue: PharmacyHodSalesRevenue;
  receipt_register: PharmacyHodReceiptRegisterRow[];
  reports_analytics: PharmacyHodReportsAnalytics;
  configuration_requests: PharmacyCatalogRegistryRow[];
  configuration_requests_enabled: boolean;
}

export const pharmacyHodService = {
  getDashboardStreamUrl(params?: {
    start_date?: string;
    end_date?: string;
  }): string {
    const baseUrl = String(client.defaults.baseURL || '').replace(/\/$/, '');
    const searchParams = new URLSearchParams();
    if (params?.start_date) searchParams.set('start_date', params.start_date);
    if (params?.end_date) searchParams.set('end_date', params.end_date);
    const query = searchParams.toString();
    return `${baseUrl}/v1/pharmacy-hod/dashboard-stream${query ? `?${query}` : ''}`;
  },

  async getDashboard(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<PharmacyHodDashboardResponse> {
    const response = await client.get('/v1/pharmacy-hod/dashboard', { params });
    return response.data;
  },

  async updateStaffAssignment(
    staffId: string,
    payload: { allowed_unit_ids: string[]; default_unit_id?: string | null }
  ): Promise<PharmacyHodStaffSummary> {
    const response = await client.put(`/v1/pharmacy-hod/staff/${staffId}/assignment`, payload);
    return response.data;
  },
};
