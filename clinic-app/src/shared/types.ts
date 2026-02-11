// /projects/clinic-monorepo/clinic-app/src/shared/types.ts
import {
  PrescriptionFulfillmentType,
  PrescriptionStatus,
  VisitStatus,
  VisitServiceLine,
} from './enums';

export interface UserDTO {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  clinic_id: string;
  is_active: boolean;
}

export interface ClinicProfileResponse {
  id: string;
  name: string;
  logo_url?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  timezone?: string | null;
  billing_currency?: string | null;
  registration_fee_minor?: number | null;
  registration_fee_required?: boolean | null;
  monthly_revenue_target_minor?: number | null;
  description?: string | null;
}

export interface ClinicRegistrationFeeResponse {
  registration_fee_minor: number;
  registration_fee_required: boolean;
  billing_currency: string;
}

export interface StaffResponse {
  id: string;
  clinic_id: string;
  full_name: string | null;
  email: string;
  role: string;
  is_active: boolean;
  specialty?: string | null;
  department?: string | null;
  room_label?: string | null;
  availability_status?: string | null;
}

export interface ApiError {
  detail: string;
  code?: string;
}

export interface VisitResponse {
  id: string;
  clinic_id: string;
  patient_id: string;
  patient_name?: string | null;
  patient_mrn?: string | null;
  consultation_status?: 'none' | 'in_progress' | 'completed' | null;
  intake_emergency_flag?: boolean | null;
  intake_emergency_reason?: string | null;
  intake_emergency_set_at?: string | null;
  assigned_doctor_id: string | null;
  service_line?: VisitServiceLine;
  status: VisitStatus;
  has_active_admission?: boolean | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ConsultationResponse {
  id: string;
  visit_id: string;
  doctor_id: string;
  doctor_full_name: string | null;
  vitals: string | null;
  presenting_complaints: string | null;
  diagnosis: string | null;
  notes: string | null;
  started_at: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PrescriptionResponse {
  id: string;
  consultation_id: string;
  visit_id: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_mrn?: string | null;
  drug_name: string;
  dosage: string;
  frequency: string;
  duration: string;
  instructions: string | null;
  status: PrescriptionStatus;
  prescribed_by: string;
  prescribed_by_name?: string | null;
  prescribed_by_role?: string | null;
  dispensed_by: string | null;
  dispensed_by_name?: string | null;
  dispensed_by_role?: string | null;
  issued_at: string;
  dispensed_at: string | null;
  cancelled_at: string | null;

  fulfillment_type?: PrescriptionFulfillmentType | null;
  fulfillment_note?: string | null;
}
