import client from '@/api/client';

export type AdmissionType = 'EMERGENCY' | 'ELECTIVE';
export type AdmissionRequestStatus =
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'CANCELLED';
export type AdmissionStatus = 'ACTIVE' | 'DISCHARGED' | 'CANCELLED';
export type AdmissionDischargeDisposition =
  | 'HOME'
  | 'TRANSFERRED_OUT'
  | 'DECEASED'
  | 'LAMA'
  | 'ELOPED'
  | 'OTHER';
export type BedAssignmentType = 'ASSIGN' | 'TRANSFER';
export type VisitServiceLine = 'OPD' | 'ANC' | 'MATERNITY';
export type VisitStatus =
  | 'REGISTERED'
  | 'TRIAGED'
  | 'IN_CONSULTATION'
  | 'LAB_REQUESTED'
  | 'LAB_COMPLETED'
  | 'PHARMACY_PENDING'
  | 'COMPLETED'
  | 'CANCELLED';

export interface BedTimelineItem {
  assignment_id: string;
  assignment_type: BedAssignmentType;
  bed_id: string;
  bed_label: string;
  ward_id: string;
  ward_name: string;
  assigned_at: string;
  released_at?: string | null;
  reason?: string | null;
  assigned_by: string;
  assigned_by_name?: string | null;
  from_bed_label?: string | null;
}

export interface AdmissionRequest {
  id: string;
  clinic_id: string;
  patient_id: string;
  admission_type: AdmissionType;
  status: AdmissionRequestStatus;
  reason: string;
  requested_by: string;
  requested_at: string;
  decided_by?: string | null;
  decided_at?: string | null;
  decision_reason?: string | null;
  admission_id?: string | null;
  admission_status?: AdmissionStatus | null;
  has_active_bed_assignment?: boolean;
  current_bed_id?: string | null;
  current_bed_label?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  active_visit_id?: string | null;
  active_visit_status?: VisitStatus | null;
  active_visit_service_line?: VisitServiceLine | null;
  active_visit_owner_id?: string | null;
  active_visit_owner_name?: string | null;
  active_visit_version?: number | null;
  can_assign_bed?: boolean;
  can_reassign_bed?: boolean;
  can_reassign_owner?: boolean;
  action_blockers?: string[];
  bed_timeline?: BedTimelineItem[];
}

export interface AdmissionRequestCreatePayload {
  patient_id: string;
  admission_type: AdmissionType;
  reason: string;
}

export interface AdmissionRequestDecisionPayload {
  reason: string;
}

export interface AdmissionDischargePayload {
  disposition: AdmissionDischargeDisposition;
  discharge_notes?: string | null;
  transferred_to_facility?: string | null;
  death_pronounced_at?: string | null;
}

export const admissionRequestService = {
  async createRequest(payload: AdmissionRequestCreatePayload): Promise<AdmissionRequest> {
    const response = await client.post('/v1/admissions/requests', payload);
    return response.data;
  },

  async listRequests(status?: AdmissionRequestStatus): Promise<AdmissionRequest[]> {
    const response = await client.get('/v1/admissions/requests', {
      params: status ? { status_filter: status } : undefined,
    });
    return response.data;
  },

  async approveRequest(
    requestId: string,
    payload: AdmissionRequestDecisionPayload
  ): Promise<AdmissionRequest> {
    const response = await client.post(
      `/v1/admissions/requests/${requestId}/approve`,
      payload
    );
    return response.data;
  },

  async rejectRequest(
    requestId: string,
    payload: AdmissionRequestDecisionPayload
  ): Promise<AdmissionRequest> {
    const response = await client.post(
      `/v1/admissions/requests/${requestId}/reject`,
      payload
    );
    return response.data;
  },

  async cancelRequest(
    requestId: string,
    payload: AdmissionRequestDecisionPayload
  ): Promise<AdmissionRequest> {
    const response = await client.post(
      `/v1/admissions/requests/${requestId}/cancel`,
      payload
    );
    return response.data;
  },

  async releaseBed(
    admissionId: string,
    payload: AdmissionRequestDecisionPayload
  ): Promise<void> {
    await client.post(`/v1/admissions/${admissionId}/bed/release`, payload);
  },

  async dischargeAdmission(
    admissionId: string,
    payload: AdmissionDischargePayload
  ): Promise<void> {
    await client.post(`/v1/admissions/${admissionId}/discharge`, payload);
  },
};
