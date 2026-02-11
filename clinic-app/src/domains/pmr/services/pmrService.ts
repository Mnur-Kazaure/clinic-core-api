// /projects/clinic-monorepo/clinic-app/src/domains/pmr/services/pmrService.ts
import client from '@/api/client';
import { PurposeOfUse } from '@/shared/enums';

export interface PMRMrnResponse {
  id: string;
  clinic_id: string;
  patient_id: string;
  mrn: string;
  status: 'ACTIVE' | 'RETIRED';
  issued_at: string;
  issued_by: string;
  check_digit: string;
  retired_at?: string | null;
  retire_reason?: string | null;
}

export interface PMRResponse {
  patient_id_requested: string;
  patient_id_canonical: string;
  access_log_id: string;
  identity_state: string;
  full_name: string;
  date_of_birth: string;
  gender: string;
  phone_number?: string | null;
  address?: string | null;
  occupation?: string | null;
  active_mrn?: PMRMrnResponse | null;
  retired_mrns: PMRMrnResponse[];
  identity_closure_ids: string[];
  visits: Array<{
    id: string;
    status: string;
    started_at: string;
    completed_at?: string | null;
    assigned_doctor_id: string;
  }>;
  admissions: Array<{
    id: string;
    status: string;
    admitted_at: string;
    discharged_at?: string | null;
    cancelled_at?: string | null;
  }>;

  effective_detail_level?: 'SUMMARY' | string;
  detail_level_downgraded?: boolean;
  clinical_history_page?: {
    limit: number;
    next_cursor?: string | null;
    has_more: boolean;
    generated_at: string;
  };
  clinical_history?: Array<{
    visit_id: string;
    visit_status: string;
    visit_started_at: string;
    visit_closed_at?: string | null;
    assigned_doctor_id?: string | null;
    sections: {
      consultation: {
        exists: boolean;
        missing_reason?: string | null;
        item?: {
          consultation_id: string;
          created_at: string;
          completed_at?: string | null;
          clinician_id: string;
          presenting_complaint_preview?: string | null;
          diagnosis_summary?: string | null;
          plan_preview?: string | null;
          note_preview: {
            text?: string | null;
            max_len: number;
            truncated: boolean;
          };
        } | null;
      };
      prescriptions: {
        exists: boolean;
        missing_reason?: string | null;
        count: number;
        items: Array<{
          prescription_id: string;
          created_at: string;
          clinician_id: string;
          status: string;
          drugs: Array<{
            name: string;
            dose?: string | null;
            frequency?: string | null;
            duration?: string | null;
          }>;
        }>;
      };
      labs: {
        exists: boolean;
        missing_reason?: string | null;
        count: number;
        requests: Array<{
          lab_request_id: string;
          created_at: string;
          ordered_by_id: string;
          status: string;
          tests: Array<{ code?: string | null; name: string }>;
          special_instructions?: string | null;
          results_available: boolean;
          results_summary: Array<{
            test_name: string;
            value?: string | null;
            unit?: string | null;
            reference_range?: string | null;
          }>;
        }>;
      };
    };
  }>;
}

export interface PMRQuery {
  purpose_of_use: PurposeOfUse;
  justification: string;
  break_glass?: boolean;
  limit?: number;
  cursor?: string;
  detail_level?: string;
}

export const pmrService = {
  async getPMR(patientId: string, params: PMRQuery): Promise<PMRResponse> {
    const response = await client.get(`/v1/pmr/patients/${patientId}`, {
      params,
    });
    return response.data;
  },
  async issueMrn(patientId: string): Promise<PMRMrnResponse> {
    const response = await client.post(`/v1/pmr/patients/${patientId}/mrn`);
    return response.data.mrn;
  },
};
