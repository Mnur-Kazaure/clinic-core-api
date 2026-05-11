import client from '@/api/client';

export interface LabManagerUnitContext {
  id: string;
  name: string;
}

export interface LabManagerOverviewMetric {
  total_tests_today: number;
  pending_verifications: number;
  critical_alerts_open: number;
  rejected_specimens: number;
  qc_failures: number;
  revenue_today_minor: number;
  blocked_unpaid_requests: number;
  active_staff_on_duty: number;
  currency: string;
  bottleneck_units: string[];
}

export interface LabManagerUnitOperation {
  unit_id: string;
  unit_name: string;
  queue_volume: number;
  staff_on_duty: number;
  pending_specimens: number;
  pending_results: number;
  pending_verifications: number;
  rejected_specimens: number;
  critical_alerts: number;
  qc_failures: number;
  completed_today: number;
  revenue_today_minor: number;
  bottleneck_labels: string[];
}

export interface LabManagerStaffSummary {
  user_id: string;
  full_name?: string | null;
  email: string;
  role: 'LAB' | 'LAB_TECH' | 'LAB_SCIENTIST' | 'LAB_SUPERVISOR' | 'LAB_MANAGER';
  is_active: boolean;
  assignment_status: 'ACTIVE' | 'TEMP_COVERAGE' | 'ON_LEAVE' | 'RESTRICTED' | 'INACTIVE';
  coverage_note?: string | null;
  allowed_units: LabManagerUnitContext[];
  default_unit_id?: string | null;
  default_unit_name?: string | null;
  recent_activity_summary?: string | null;
  recent_activity_at?: string | null;
  last_updated_at?: string | null;
  last_updated_by_id?: string | null;
  last_updated_by_name?: string | null;
}

export interface LabManagerPendingVerification {
  request_id: string;
  result_id: string;
  visit_id: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  accession_number?: string | null;
  test_name: string;
  unit_id?: string | null;
  unit_name?: string | null;
  result_status: 'DRAFT' | 'SUBMITTED' | 'VERIFIED' | 'REJECTED' | 'RELEASED' | 'AMENDED';
  abnormal: boolean;
  critical: boolean;
  waiting_minutes: number;
  entered_by?: string | null;
  entered_by_name?: string | null;
  verification_policy:
    | 'NONE'
    | 'OPTIONAL'
    | 'REQUIRED_BEFORE_RELEASE'
    | 'REQUIRED_IF_ABNORMAL'
    | 'REQUIRED_IF_CRITICAL';
  created_at: string;
}

export interface LabManagerCriticalAlert {
  alert_id: string;
  result_id?: string | null;
  request_item_id?: string | null;
  visit_id?: string | null;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  unit_id?: string | null;
  unit_name?: string | null;
  test_name?: string | null;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'CREATED' | 'DELIVERED' | 'ACKNOWLEDGED' | 'ESCALATED' | 'RESOLVED' | 'CANCELLED';
  message: string;
  created_at: string;
  acknowledged_at?: string | null;
  escalated_at?: string | null;
  resolved_at?: string | null;
}

export interface LabManagerSpecimenIssue {
  specimen_id: string;
  accession_number: string;
  request_item_id: string;
  visit_id: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  unit_id: string;
  unit_name?: string | null;
  test_name: string;
  status: string;
  issue_type: string;
  rejection_reason_code?: string | null;
  rejection_reason_text?: string | null;
  responsible_staff_id?: string | null;
  responsible_staff_name?: string | null;
  updated_at: string;
}

export interface LabManagerQualityControlRun {
  qc_run_id: string;
  unit_id: string;
  unit_name?: string | null;
  machine_id?: string | null;
  qc_level: string;
  status: 'PASS' | 'FAIL' | 'WARNING';
  performed_by: string;
  performed_by_name?: string | null;
  performed_at: string;
  fail_count: number;
  warning_count: number;
  override_count: number;
  unresolved: boolean;
  notes?: string | null;
}

export interface LabManagerQualityControlSummary {
  total_runs: number;
  fail_runs: number;
  warning_runs: number;
  override_events: number;
  unresolved_failures: number;
  runs: LabManagerQualityControlRun[];
}

export interface LabManagerActivityAuditItem {
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
  visit_id?: string | null;
  request_item_id?: string | null;
  result_id?: string | null;
  specimen_id?: string | null;
  accession_number?: string | null;
  receipt_number?: string | null;
  summary: string;
  detail?: string | null;
  severity: string;
  metadata_json?: Record<string, unknown> | unknown[] | null;
}

export interface LabManagerStaffPerformance {
  user_id: string;
  full_name?: string | null;
  role: 'LAB' | 'LAB_TECH' | 'LAB_SCIENTIST' | 'LAB_SUPERVISOR' | 'LAB_MANAGER';
  unit_names: string[];
  workload_volume: number;
  specimens_handled: number;
  results_entered: number;
  verifications_completed: number;
  releases_completed: number;
  qc_entries: number;
  qc_overrides: number;
  pending_load: number;
  patients_touched: number;
  specimen_issue_rate: number;
  average_release_turnaround_minutes?: number | null;
}

export interface LabManagerRevenueByUnit {
  unit_id?: string | null;
  unit_name: string;
  revenue_minor: number;
}

export interface LabManagerSalesRevenueRow {
  receipt_id: string;
  receipt_number: string;
  occurred_at: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  visit_id: string;
  test_name: string;
  unit_id?: string | null;
  unit_name?: string | null;
  quantity: number;
  amount_minor: number;
  currency: string;
  payment_method: 'CASH' | 'CARD' | 'TRANSFER';
  cashier_name?: string | null;
  status: string;
}

export interface LabManagerSalesRevenueSummary {
  total_revenue_minor: number;
  paid_tests_count: number;
  receipt_count: number;
  blocked_unpaid_count: number;
  currency: string;
  revenue_by_unit: LabManagerRevenueByUnit[];
  rows: LabManagerSalesRevenueRow[];
}

export interface LabManagerReceiptRegisterRow {
  receipt_id: string;
  receipt_number: string;
  occurred_at: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  visit_id: string;
  cashier_name?: string | null;
  amount_minor: number;
  currency: string;
  payment_method: 'CASH' | 'CARD' | 'TRANSFER';
  status: string;
  unit_names: string[];
  linked_test_items: string[];
}

export interface LabManagerReceiptRegister {
  currency: string;
  rows: LabManagerReceiptRegisterRow[];
}

export interface LabManagerDateMetric {
  label: string;
  count: number;
  amount_minor?: number | null;
}

export interface LabManagerNamedCountMetric {
  label: string;
  count: number;
}

export interface LabManagerReportsAnalytics {
  test_volume_by_day: LabManagerDateMetric[];
  revenue_by_unit: LabManagerRevenueByUnit[];
  common_tests_ordered: LabManagerNamedCountMetric[];
  critical_result_frequency: LabManagerNamedCountMetric[];
  specimen_rejection_trend: LabManagerDateMetric[];
  verification_turnaround_minutes?: number | null;
  completion_turnaround_minutes?: number | null;
  qc_pass_fail_trend: LabManagerNamedCountMetric[];
  staff_workload_trend: LabManagerNamedCountMetric[];
}

export interface LabManagerConfigurationRequest {
  id: string;
  request_type:
    | 'NEW_STAFF_ACCOUNT'
    | 'ROLE_ADJUSTMENT'
    | 'NEW_TEST_ACTIVATION'
    | 'PRICE_REVIEW'
    | 'TEMPLATE_ADJUSTMENT'
    | 'UNIT_CONFIGURATION_CHANGE';
  status: 'PENDING' | 'IN_REVIEW' | 'APPROVED' | 'REJECTED' | 'COMPLETED';
  department_name: string;
  justification: string;
  requested_by: string;
  requested_by_name?: string | null;
  linked_staff_id?: string | null;
  linked_staff_name?: string | null;
  linked_unit_id?: string | null;
  linked_unit_name?: string | null;
  linked_test_code?: string | null;
  request_payload_json?: Record<string, unknown> | unknown[] | null;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
}

export type LabManagerBadgeSectionKey =
  | 'PENDING_VERIFICATIONS'
  | 'CRITICAL_ALERTS'
  | 'SPECIMEN_ISSUES'
  | 'QUALITY_CONTROL'
  | 'SALES_REVENUE'
  | 'RECEIPT_REGISTER';

export interface LabManagerBadgeState {
  section_key: LabManagerBadgeSectionKey;
  count: number;
  tone: 'critical' | 'warning' | 'info';
  last_viewed_at?: string | null;
}

export interface LabManagerBadgeSnapshot {
  generated_at: string;
  sections: LabManagerBadgeState[];
}

export interface LabManagerDashboard {
  date_range_start: string;
  date_range_end: string;
  units: LabManagerUnitContext[];
  overview: LabManagerOverviewMetric;
  unit_operations: LabManagerUnitOperation[];
  staff: LabManagerStaffSummary[];
  pending_verifications: LabManagerPendingVerification[];
  critical_alerts: LabManagerCriticalAlert[];
  specimen_issues: LabManagerSpecimenIssue[];
  quality_control: LabManagerQualityControlSummary;
  activity_audit: LabManagerActivityAuditItem[];
  staff_performance: LabManagerStaffPerformance[];
  sales_revenue: LabManagerSalesRevenueSummary;
  receipt_register: LabManagerReceiptRegister;
  reports_analytics: LabManagerReportsAnalytics;
  configuration_requests: LabManagerConfigurationRequest[];
}

export interface LabManagerStaffAssignmentUpdateRequest {
  allowed_lab_unit_ids: string[];
  default_lab_unit_id?: string | null;
  assignment_status?: 'ACTIVE' | 'TEMP_COVERAGE' | 'ON_LEAVE' | 'RESTRICTED' | 'INACTIVE';
  coverage_note?: string | null;
}

export interface LabManagerConfigurationRequestCreate {
  request_type:
    | 'NEW_STAFF_ACCOUNT'
    | 'ROLE_ADJUSTMENT'
    | 'NEW_TEST_ACTIVATION'
    | 'PRICE_REVIEW'
    | 'TEMPLATE_ADJUSTMENT'
    | 'UNIT_CONFIGURATION_CHANGE';
  justification: string;
  linked_staff_id?: string | null;
  linked_unit_id?: string | null;
  linked_test_code?: string | null;
  request_payload_json?: Record<string, unknown> | unknown[] | null;
}

export const labManagerService = {
  getBadgeStreamUrl(): string {
    const baseUrl = String(client.defaults.baseURL || '').replace(/\/$/, '');
    return `${baseUrl}/v1/lab/manager/badge-stream`;
  },

  async getBadges(): Promise<LabManagerBadgeSnapshot> {
    const response = await client.get('/v1/lab/manager/badges');
    return response.data;
  },

  async markBadgeViewed(sectionKey: LabManagerBadgeSectionKey): Promise<LabManagerBadgeSnapshot> {
    const response = await client.post(`/v1/lab/manager/badges/${sectionKey}/viewed`);
    return response.data;
  },

  async getDashboard(startDate?: string, endDate?: string): Promise<LabManagerDashboard> {
    const params: Record<string, string> = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const response = await client.get('/v1/lab/manager/dashboard', { params });
    return response.data;
  },

  async updateStaffAssignment(
    staffId: string,
    payload: LabManagerStaffAssignmentUpdateRequest
  ): Promise<LabManagerStaffSummary> {
    const response = await client.patch(`/v1/lab/manager/staff/${staffId}/assignment`, payload);
    return response.data;
  },

  async createConfigurationRequest(
    payload: LabManagerConfigurationRequestCreate
  ): Promise<LabManagerConfigurationRequest> {
    const response = await client.post('/v1/lab/manager/configuration-requests', payload);
    return response.data;
  },
};
