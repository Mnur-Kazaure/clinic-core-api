// /projects/clinic-monorepo/clinic-app/src/shared/types.ts
import {
  PharmacyExceptionAuthorizationType,
  PharmacyPrescriptionWorkflowStatus,
  PrescriptionFulfillmentType,
  PrescriptionStatus,
  VisitTriageState,
  VisitStatus,
  VisitServiceLine,
} from './enums';

export interface UserDTO {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  clinic_id: string;
  current_department_id?: string | null;
  current_department_name?: string | null;
  allowed_department_ids?: string[];
  allowed_departments?: DepartmentContextDTO[];
  default_lab_unit_id?: string | null;
  allowed_lab_unit_ids?: string[];
  allowed_lab_units?: LabUnitContextDTO[];
  default_pharmacy_unit_id?: string | null;
  allowed_pharmacy_unit_ids?: string[];
  allowed_pharmacy_units?: PharmacyUnitContextDTO[];
  default_cashier_pay_point_id?: string | null;
  allowed_cashier_pay_point_ids?: string[];
  allowed_cashier_pay_points?: CashierPayPointContextDTO[];
  is_active: boolean;
}

export interface DepartmentContextDTO {
  id: string;
  name: string;
  is_primary: boolean;
}

export interface LabUnitContextDTO {
  id: string;
  name: string;
}

export interface PharmacyUnitContextDTO {
  id: string;
  name: string;
}

export interface CashierPayPointContextDTO {
  id: string;
  name: string;
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
  default_lab_unit_id?: string | null;
  default_lab_unit_name?: string | null;
  allowed_lab_units?: LabUnitContextDTO[];
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
  service_line_id?: string | null;
  status: VisitStatus;
  triage_state?: VisitTriageState;
  triage_acuity?: 'CRITICAL' | 'URGENT' | 'ROUTINE' | null;
  triaged_at?: string | null;
  triaged_by?: string | null;
  linked_follow_up_id?: string | null;
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
  recall_suggestions?: RecallSuggestionDTO[];
}

export interface RecallSuggestionDTO {
  condition_profile_id: string;
  condition_code: string;
  display_name: string;
  default_interval_value: number;
  default_interval_unit: 'DAYS' | 'WEEKS' | 'MONTHS';
  default_priority: 'ROUTINE' | 'IMPORTANT' | 'CRITICAL';
  confidence: 'HIGH' | 'LOW';
}

export interface PrescriptionStockLotOptionResponse {
  id: string;
  batch_number: string;
  expiry_date?: string | null;
  quantity_on_hand: number;
  low_stock: boolean;
  blocked: boolean;
}

export interface PrescriptionReassignmentOptionResponse {
  unit_id: string;
  unit_name: string;
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
  quantity_prescribed: number;
  quantity_dispensed_total: number;
  quantity_remaining: number;
  status: PrescriptionStatus;
  workflow_status: PharmacyPrescriptionWorkflowStatus;
  billing_item_id?: string | null;
  billing_status?: string | null;
  assigned_dispensing_unit_id?: string | null;
  assigned_dispensing_unit_name?: string | null;
  assigned_cashier_pay_point_id?: string | null;
  assigned_cashier_pay_point_name?: string | null;
  exception_authorization_type?: PharmacyExceptionAuthorizationType;
  payment_cleared?: boolean | null;
  source_department_name?: string | null;
  priority?: 'ROUTINE' | 'URGENT' | 'EMERGENCY' | null;
  aging_minutes?: number | null;
  local_stock_status?: string | null;
  local_stock_available_quantity?: number | null;
  local_stock_source?: string | null;
  available_stock_lots?: PrescriptionStockLotOptionResponse[];
  reassignment_options?: PrescriptionReassignmentOptionResponse[];
  prescribed_by: string;
  prescribed_by_name?: string | null;
  prescribed_by_role?: string | null;
  dispensed_by: string | null;
  dispensed_by_name?: string | null;
  dispensed_by_role?: string | null;
  issued_at: string;
  dispensed_at: string | null;
  cancelled_at: string | null;
  externally_fulfilled_at?: string | null;

  fulfillment_type?: PrescriptionFulfillmentType | null;
  fulfillment_note?: string | null;
}
