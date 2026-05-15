import client from '@/api/client';
import { LabRequest, LabResult } from '@/domains/lab/services/labService';
import { PurposeOfUse } from '@/shared/enums';

export interface DoctorLabVisitResultSummary {
  result_id: string;
  lab_request_id: string;
  request_item_id?: string | null;
  test_name: string;
  test_code?: string | null;
  unit_id?: string | null;
  unit_name?: string | null;
  requested_at: string;
  released_at: string;
  status: 'RELEASED' | 'AMENDED' | 'VERIFIED' | 'SUBMITTED' | 'DRAFT' | 'REJECTED';
  has_abnormal: boolean;
  has_critical: boolean;
  is_amended: boolean;
  is_superseded: boolean;
  critical_alert_count: number;
  accession_numbers: string[];
  specimen_count: number;
}

export interface DoctorLabResultFieldValue {
  template_field_id?: string | null;
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
  unit?: string | null;
  reference_range_text?: string | null;
  reference_min?: number | null;
  reference_max?: number | null;
  reference_unit?: string | null;
  options_json?: string[] | Record<string, unknown> | null;
  value_string?: string | null;
  value_number?: number | null;
  value_boolean?: boolean | null;
  value_json?: Record<string, unknown> | unknown[] | null;
  abnormal_flag: boolean;
  critical_flag: boolean;
}

export interface DoctorLabSpecimenContext {
  specimen_id: string;
  accession_number: string;
  specimen_type: string;
  specimen_source: string;
  container_type?: string | null;
  collection_site?: string | null;
  specimen_sequence: number;
  specimen_label_suffix?: string | null;
  status: string;
  collected_at?: string | null;
  received_at?: string | null;
}

export interface DoctorLabResultAlert {
  alert_id: string;
  alert_type: string;
  severity: string;
  status: string;
  message: string;
  created_at: string;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
  escalated_at?: string | null;
}

export interface DoctorLabResultVersion {
  result_id: string;
  released_at?: string | null;
  entered_at: string;
  status: string;
  is_amended: boolean;
  is_superseded: boolean;
  amendment_reason?: string | null;
}

export interface DoctorLabResultAttachment {
  attachment_type: string;
  uploaded_by: string;
  uploaded_at: string;
  source: string;
  file_name: string;
  file_url: string;
}

export interface DoctorLabResultDetail {
  result_id: string;
  visit_id: string;
  patient_id: string;
  patient_name: string;
  patient_mrn?: string | null;
  test_name: string;
  test_code?: string | null;
  unit_id?: string | null;
  unit_name?: string | null;
  requested_at: string;
  status: string;
  released_at?: string | null;
  entered_at: string;
  verified_at?: string | null;
  entered_by?: string | null;
  entered_by_name?: string | null;
  verified_by?: string | null;
  verified_by_name?: string | null;
  released_by?: string | null;
  released_by_name?: string | null;
  accession_numbers: string[];
  has_abnormal: boolean;
  has_critical: boolean;
  is_amended: boolean;
  is_superseded: boolean;
  state_labels: string[];
  amendment_reason?: string | null;
  values: DoctorLabResultFieldValue[];
  specimens: DoctorLabSpecimenContext[];
  alerts: DoctorLabResultAlert[];
  prior_versions: DoctorLabResultVersion[];
  attachments: DoctorLabResultAttachment[];
}

export interface DoctorPatientLabHistoryEntry {
  result_id: string;
  visit_id: string;
  released_at: string;
  test_name: string;
  test_code?: string | null;
  has_abnormal: boolean;
  has_critical: boolean;
  is_amended: boolean;
  accession_numbers: string[];
  values: DoctorLabResultFieldValue[];
}

export const doctorLabService = {
  async getLabRequestsByVisit(
    visitId: string,
    options?: {
      purpose_of_use?: PurposeOfUse;
      justification?: string;
      break_glass?: boolean;
    }
  ): Promise<LabRequest[]> {
    const purpose_of_use = options?.purpose_of_use ?? PurposeOfUse.TREATMENT;
    const justification = options?.justification ?? 'Lab review';
    const break_glass = options?.break_glass ?? false;
    const response = await client.get(
      `/v1/doctor/visits/${visitId}/lab-requests`,
      {
        params: {
          purpose_of_use,
          justification,
          break_glass,
        },
      }
    );
    return response.data;
  },

  async getLabResultsForRequest(
    requestId: string,
    options?: {
      purpose_of_use?: PurposeOfUse;
      justification?: string;
      break_glass?: boolean;
    }
  ): Promise<LabResult[]> {
    const purpose_of_use = options?.purpose_of_use ?? PurposeOfUse.TREATMENT;
    const justification = options?.justification ?? 'Lab review';
    const break_glass = options?.break_glass ?? false;
    const response = await client.get(
      `/v1/doctor/lab-requests/${requestId}/results`,
      {
        params: {
          purpose_of_use,
          justification,
          break_glass,
        },
      }
    );
    return response.data;
  },

  async getVisitLabResults(
    visitId: string,
    options?: {
      purpose_of_use?: PurposeOfUse;
      justification?: string;
      break_glass?: boolean;
    }
  ): Promise<DoctorLabVisitResultSummary[]> {
    const purpose_of_use = options?.purpose_of_use ?? PurposeOfUse.TREATMENT;
    const justification = options?.justification ?? 'Visit lab result review';
    const break_glass = options?.break_glass ?? false;
    const response = await client.get(`/v1/doctor/visits/${visitId}/lab-results`, {
      params: {
        purpose_of_use,
        justification,
        break_glass,
      },
    });
    return response.data;
  },

  async getVisitLabResultDetail(
    visitId: string,
    resultId: string,
    options?: {
      purpose_of_use?: PurposeOfUse;
      justification?: string;
      break_glass?: boolean;
    }
  ): Promise<DoctorLabResultDetail> {
    const purpose_of_use = options?.purpose_of_use ?? PurposeOfUse.TREATMENT;
    const justification = options?.justification ?? 'Visit lab result review';
    const break_glass = options?.break_glass ?? false;
    const response = await client.get(
      `/v1/doctor/visits/${visitId}/lab-results/${resultId}`,
      {
        params: {
          purpose_of_use,
          justification,
          break_glass,
        },
      }
    );
    return response.data;
  },

  async getPatientLabHistory(
    patientId: string,
    testCode: string,
    options?: {
      purpose_of_use?: PurposeOfUse;
      justification?: string;
      break_glass?: boolean;
    }
  ): Promise<DoctorPatientLabHistoryEntry[]> {
    const purpose_of_use = options?.purpose_of_use ?? PurposeOfUse.TREATMENT;
    const justification = options?.justification ?? 'Longitudinal lab history review';
    const break_glass = options?.break_glass ?? false;
    const response = await client.get(
      `/v1/doctor/patients/${patientId}/lab-history/${encodeURIComponent(testCode)}`,
      {
        params: {
          purpose_of_use,
          justification,
          break_glass,
        },
      }
    );
    return response.data;
  },
};
