import client from '@/api/client';
import { v4 as uuidv4 } from 'uuid';
import { PurposeOfUse } from '@/shared/enums';

export interface LabRequest {
  id: string;
  visit_id: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  test_name: string;
  test_code?: string | null;
  special_instructions?: string | null;
  status: 'PENDING' | 'COMPLETED' | 'CANCELLED';
  requested_by: string;
  requested_by_name?: string | null;
  requested_by_role?: string | null;
  billing_item_id?: string | null;
  billing_status?: string | null;
  billing_total_minor?: number | null;
  billing_currency?: string | null;
  payment_verified?: boolean | null;
  workflow_status?:
    | 'ORDERED'
    | 'PAID'
    | 'AWAITING_SPECIMEN'
    | 'IN_ANALYSIS'
    | 'RESULT_ENTERED'
    | 'VERIFIED'
    | 'RELEASED'
    | 'COMPLETED'
    | null;
  target_unit_id?: string | null;
  target_unit_name?: string | null;
  ready_specimen_count?: number;
  critical_alert_count?: number;
  active_result_id?: string | null;
  latest_result_status?:
    | 'DRAFT'
    | 'SUBMITTED'
    | 'VERIFIED'
    | 'REJECTED'
    | 'RELEASED'
    | 'AMENDED'
    | null;
  created_at: string;
  completed_at: string | null;
}

export interface LabWorkspaceOverview {
  unit_id: string;
  unit_name: string;
  pending_requests: number;
  awaiting_specimen: number;
  pending_verifications: number;
  critical_alerts: number;
  completed_today: number;
  qc_failures: number;
  unrouted_requests: number;
}

export type LabWorkspaceAttentionKey =
  | 'PENDING_QUEUE'
  | 'AWAITING_SPECIMEN'
  | 'PENDING_VERIFICATIONS'
  | 'CRITICAL_ALERTS'
  | 'QC_FAILURES'
  | 'COMPLETED_TODAY';

export type LabWorkspaceTabKey = 'QUEUE' | 'SPECIMENS' | 'RESULTS' | 'COMPLETED' | 'QC';

export interface LabWorkspaceAttentionItem {
  key: LabWorkspaceAttentionKey;
  label: string;
  count: number;
  tone: 'critical' | 'warning' | 'info' | 'success' | string;
  target_tab: LabWorkspaceTabKey;
}

export interface LabWorkspaceTabBadge {
  tab_key: LabWorkspaceTabKey;
  count: number;
  tone: 'critical' | 'warning' | 'info' | 'success' | string;
}

export interface LabWorkspaceBenchSnapshot {
  generated_at: string;
  unit_id: string;
  unit_name: string;
  pending_requests: number;
  awaiting_specimen: number;
  pending_verifications: number;
  critical_alerts: number;
  completed_today: number;
  qc_failures: number;
  unrouted_requests: number;
  specimen_issue_count: number;
  result_workbench_count: number;
  queue_count: number;
  qc_attention_count: number;
  attention_items: LabWorkspaceAttentionItem[];
  tab_badges: LabWorkspaceTabBadge[];
}

export interface LabResultCreate {
  result_value: string;
  result_unit?: string | null;
  reference_range?: string | null;
}

export interface LabResultTemplateField {
  id: string;
  field_code: string;
  field_name: string;
  field_type:
    | 'STRING'
    | 'NUMBER'
    | 'BOOLEAN'
    | 'SELECT'
    | 'TEXT'
    | 'JSON'
    | 'ATTACHMENT';
  display_order: number;
  is_required: boolean;
  unit?: string | null;
  reference_range_text?: string | null;
  reference_min?: number | null;
  reference_max?: number | null;
  reference_unit?: string | null;
  options_json?: string[] | Record<string, unknown> | null;
  validation_rules_json?: Record<string, unknown> | unknown[] | null;
}

export interface LabResultTemplate {
  id: string;
  code: string;
  name: string;
  result_type: string;
  version: number;
  description?: string | null;
  is_active: boolean;
  fields: LabResultTemplateField[];
}

export interface LabSpecimen {
  id: string;
  clinic_id: string;
  accession_number: string;
  request_item_id: string;
  target_unit_id: string;
  specimen_type: string;
  specimen_source: string;
  container_type?: string | null;
  collection_site?: string | null;
  specimen_sequence: number;
  specimen_label_suffix?: string | null;
  collected_by?: string | null;
  collected_at?: string | null;
  received_by?: string | null;
  received_at?: string | null;
  status: string;
  rejection_reason_code?: string | null;
  rejection_reason_text?: string | null;
  rejected_by?: string | null;
  rejected_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LabSpecimenCreatePayload {
  target_unit_id?: string | null;
  specimen_type: string;
  specimen_source: string;
  container_type?: string | null;
  collection_site?: string | null;
  specimen_sequence?: number;
  specimen_label_suffix?: string | null;
  status?: 'PENDING_COLLECTION' | 'COLLECTED' | 'RECEIVED';
  collected_at?: string | null;
  received_at?: string | null;
  print_label?: boolean;
}

export interface LabWorkspaceSpecimenSummary extends LabSpecimen {
  visit_id: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  test_name: string;
  target_unit_name?: string | null;
}

export interface StructuredLabResultValueInput {
  template_field_id: string;
  value_string?: string | null;
  value_number?: number | null;
  value_boolean?: boolean | null;
  value_json?: Record<string, unknown> | unknown[] | null;
}

export interface StructuredLabResultCreate {
  values: StructuredLabResultValueInput[];
}

export interface LabResult {
  id: string;
  lab_request_id: string;
  request_item_id?: string | null;
  result_value: string;
  result_unit?: string | null;
  reference_range?: string | null;
  technician_id: string;
  status?: string;
  entered_by?: string | null;
  entered_at?: string | null;
  verified_by?: string | null;
  verified_at?: string | null;
  released_by?: string | null;
  released_at?: string | null;
  amended_from_result_id?: string | null;
  amendment_reason?: string | null;
  created_at: string;
}

export interface LabResultActionResponse {
  result_id: string;
  status: 'DRAFT' | 'SUBMITTED' | 'VERIFIED' | 'REJECTED' | 'RELEASED' | 'AMENDED';
  verification_policy:
    | 'NONE'
    | 'OPTIONAL'
    | 'REQUIRED_BEFORE_RELEASE'
    | 'REQUIRED_IF_ABNORMAL'
    | 'REQUIRED_IF_CRITICAL';
  critical_alert_count: number;
}

export interface LabResultReleasePayload {
  qc_override_reason?: string | null;
}

export interface LabWorkspaceQcRunSummary {
  id: string;
  unit_id: string;
  unit_name?: string | null;
  machine_id?: string | null;
  qc_level: string;
  status: 'PASS' | 'FAIL' | 'WARNING';
  performed_by: string;
  performed_at: string;
  fail_count: number;
  warning_count: number;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LabManagerUnitMetric {
  unit_id: string;
  unit_name: string;
  pending_requests: number;
  awaiting_specimen: number;
  pending_verifications: number;
  critical_alerts: number;
  qc_failures: number;
  specimen_issues: number;
  completed_today: number;
}

export interface LabManagerRequestSummary {
  request_id: string;
  visit_id: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  test_name: string;
  status: string;
  workflow_status: string;
  unit_id?: string | null;
  unit_name?: string | null;
  latest_result_id?: string | null;
  latest_result_status?: string | null;
  created_at: string;
}

export interface LabManagerCriticalAlertSummary {
  alert_id: string;
  result_id?: string | null;
  request_item_id?: string | null;
  visit_id?: string | null;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  test_name?: string | null;
  unit_id?: string | null;
  unit_name?: string | null;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'CREATED' | 'DELIVERED' | 'ACKNOWLEDGED' | 'ESCALATED' | 'RESOLVED' | 'CANCELLED';
  message: string;
  created_at: string;
}

export interface LabManagerQcFailureSummary {
  qc_run_id: string;
  qc_result_id: string;
  unit_id: string;
  unit_name?: string | null;
  qc_level: string;
  analyte_name: string;
  expected_min?: number | null;
  expected_max?: number | null;
  observed_value: number;
  performed_at: string;
}

export interface LabManagerSpecimenIssueSummary {
  specimen_id: string;
  accession_number: string;
  request_item_id: string;
  visit_id: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  test_name: string;
  unit_id: string;
  unit_name?: string | null;
  status: string;
  rejection_reason_code?: string | null;
  rejection_reason_text?: string | null;
  updated_at: string;
}

export interface LabManagerOverview {
  total_pending_requests: number;
  total_pending_verifications: number;
  total_critical_alerts: number;
  total_qc_failures: number;
  total_specimen_issues: number;
  unrouted_requests: number;
  unit_metrics: LabManagerUnitMetric[];
  pending_verifications: LabManagerRequestSummary[];
  critical_alerts: LabManagerCriticalAlertSummary[];
  qc_failures: LabManagerQcFailureSummary[];
  specimen_issues: LabManagerSpecimenIssueSummary[];
}

export interface LabCompletionResponse {
  lab_request_id: string;
  visit_id: string;
  status: 'COMPLETED';
  completed_at: string;
  visit_status?: string | null;
  visit_ready_for_transition: boolean;
  suggested_next_visit_status?: 'LAB_COMPLETED' | null;
  visit_transition_expected_version?: number | null;
}

export interface LabWorkflowStatusChip {
  key: 'payment' | 'specimen' | 'result' | 'completion' | string;
  label: string;
  value: string;
  tone: 'success' | 'warning' | 'info' | 'critical' | string;
}

export interface LabWorkflowChecklistItem {
  key: string;
  label: string;
  state: 'complete' | 'pending' | 'blocked' | string;
  detail?: string | null;
}

export interface LabSpecimenDefaults {
  specimen_type?: string | null;
  specimen_source?: string | null;
  container_type?: string | null;
  collection_site?: string | null;
}

export interface LabRequestWorkflowState {
  request_id: string;
  request_status: string;
  workflow_status?: string | null;
  unit_id?: string | null;
  unit_name?: string | null;
  verification_policy:
    | 'NONE'
    | 'OPTIONAL'
    | 'REQUIRED_BEFORE_RELEASE'
    | 'REQUIRED_IF_ABNORMAL'
    | 'REQUIRED_IF_CRITICAL';
  completion_message: string;
  can_complete: boolean;
  status_chips: LabWorkflowStatusChip[];
  checklist: LabWorkflowChecklistItem[];
  specimen_defaults: LabSpecimenDefaults;
}

export const labService = {
  async getRequests(
    status?: 'PENDING' | 'COMPLETED' | 'CANCELLED',
    options?: {
      unit_id?: string;
      workflow_status?:
        | 'ORDERED'
        | 'PAID'
        | 'AWAITING_SPECIMEN'
        | 'IN_ANALYSIS'
        | 'RESULT_ENTERED'
        | 'VERIFIED'
        | 'RELEASED'
        | 'COMPLETED';
    }
  ): Promise<LabRequest[]> {
    const params: Record<string, string> = {};
    if (status) params.status = status;
    if (options?.unit_id) params.unit_id = options.unit_id;
    if (options?.workflow_status) params.workflow_status = options.workflow_status;
    const response = await client.get('/v1/lab/requests', { params });
    return response.data;
  },

  async getWorkspaceOverview(unitId: string): Promise<LabWorkspaceOverview> {
    const response = await client.get('/v1/lab/workspace/overview', {
      params: { unit_id: unitId },
    });
    return response.data;
  },

  async getWorkspaceBenchSnapshot(unitId: string): Promise<LabWorkspaceBenchSnapshot> {
    const response = await client.get('/v1/lab/workspace/bench', {
      params: { unit_id: unitId },
    });
    return response.data;
  },

  async getWorkspaceSpecimens(
    unitId: string,
    status?: string
  ): Promise<LabWorkspaceSpecimenSummary[]> {
    const params: Record<string, string> = { unit_id: unitId };
    if (status) params.status = status;
    const response = await client.get('/v1/lab/workspace/specimens', { params });
    return response.data;
  },

  async getWorkspaceQcRuns(unitId: string): Promise<LabWorkspaceQcRunSummary[]> {
    const response = await client.get('/v1/lab/workspace/qc-runs', {
      params: { unit_id: unitId },
    });
    return response.data;
  },

  getWorkspaceBenchStreamUrl(unitId: string): string {
    const baseUrl = String(client.defaults.baseURL || '').replace(/\/$/, '');
    const params = new URLSearchParams({ unit_id: unitId });
    return `${baseUrl}/v1/lab/workspace/bench-stream?${params.toString()}`;
  },

  async getManagerOverview(): Promise<LabManagerOverview> {
    const response = await client.get('/v1/lab/manager/overview');
    return response.data;
  },

  async getResults(
    requestId: string,
    options?: {
      purpose_of_use?: PurposeOfUse;
      justification?: string;
      break_glass?: boolean;
      unit_id?: string;
    }
  ): Promise<LabResult[]> {
    const purpose_of_use = options?.purpose_of_use ?? PurposeOfUse.TREATMENT;
    const justification = options?.justification ?? 'Lab result review';
    const break_glass = options?.break_glass ?? false;
    const response = await client.get(`/v1/lab/requests/${requestId}/results`, {
      params: {
        purpose_of_use,
        justification,
        break_glass,
        unit_id: options?.unit_id,
      },
    });
    return response.data;
  },

  async recordResults(
    requestId: string,
    data: LabResultCreate,
    unitId?: string
  ): Promise<LabResult> {
    const response = await client.post(
      `/v1/lab/requests/${requestId}/results`,
      data,
      { params: unitId ? { unit_id: unitId } : undefined }
    );
    return response.data;
  },

  async getResultTemplate(requestId: string, unitId?: string): Promise<LabResultTemplate> {
    const response = await client.get(`/v1/lab/requests/${requestId}/template`, {
      params: unitId ? { unit_id: unitId } : undefined,
    });
    return response.data;
  },

  async getSpecimens(requestId: string, unitId?: string): Promise<LabSpecimen[]> {
    const response = await client.get(`/v1/lab/requests/${requestId}/specimens`, {
      params: unitId ? { unit_id: unitId } : undefined,
    });
    return response.data;
  },

  async getWorkflowState(
    requestId: string,
    unitId?: string
  ): Promise<LabRequestWorkflowState> {
    const response = await client.get(`/v1/lab/requests/${requestId}/workflow-state`, {
      params: unitId ? { unit_id: unitId } : undefined,
    });
    return response.data;
  },

  async createSpecimen(
    requestId: string,
    payload: LabSpecimenCreatePayload,
    unitId?: string
  ): Promise<LabSpecimen> {
    const response = await client.post(`/v1/lab/requests/${requestId}/specimens`, payload, {
      params: unitId ? { unit_id: unitId } : undefined,
    });
    return response.data;
  },

  async recordStructuredResults(
    requestId: string,
    payload: StructuredLabResultCreate,
    unitId?: string
  ): Promise<unknown> {
    const response = await client.post(
      `/v1/lab/requests/${requestId}/structured-results`,
      payload,
      { params: unitId ? { unit_id: unitId } : undefined }
    );
    return response.data;
  },

  async completeRequest(requestId: string, unitId?: string): Promise<LabCompletionResponse> {
    const response = await client.post(`/v1/lab/requests/${requestId}/complete`, null, {
      params: unitId ? { unit_id: unitId } : undefined,
    });
    return response.data;
  },

  async verifyResult(
    resultId: string,
    unitId?: string
  ): Promise<LabResultActionResponse> {
    const response = await client.post(`/v1/lab/results/${resultId}/verify`, null, {
      params: unitId ? { unit_id: unitId } : undefined,
    });
    return response.data;
  },

  async releaseResult(
    resultId: string,
    payload?: LabResultReleasePayload,
    unitId?: string
  ): Promise<LabResultActionResponse> {
    const response = await client.post(
      `/v1/lab/results/${resultId}/release`,
      payload ?? null,
      {
        params: unitId ? { unit_id: unitId } : undefined,
      }
    );
    return response.data;
  },

  async completeVisitLab(
    visitId: string,
    expectedVersion: number
  ): Promise<unknown> {
    const idempotencyKey = `lab-complete-${visitId}-${uuidv4()}`;
    const response = await client.post(
      `/v1/visits/${visitId}/transition`,
      {
        to_status: 'LAB_COMPLETED',
        expected_version: expectedVersion,
      },
      {
        headers: {
          'Idempotency-Key': idempotencyKey,
        },
      }
    );
    return response.data;
  },
};
