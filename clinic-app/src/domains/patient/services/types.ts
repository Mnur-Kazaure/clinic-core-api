// /projects/clinic-monorepo/clinic-app/src/domains/patient/services/types.ts
export interface PatientResponse {
  id: string;
  clinic_id: string;
  full_name: string;
  date_of_birth: string; // "YYYY-MM-DD"
  gender: 'MALE' | 'FEMALE' | 'UNKNOWN';
  phone_number: string;
  address: string;
  occupation: string;
  patient_mrn?: string | null;
  identity_state?: 'PROVISIONAL' | 'VERIFIED' | 'MERGED' | 'SPLIT';
  created_reason?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}
