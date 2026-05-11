import client from '@/api/client';

export interface PrescriptionCreateRequest {
  consultation_id: string;
  pharmacy_catalog_item_id?: string;
  drug_name?: string;
  dosage: string;
  frequency: string;
  duration: string;
  quantity_prescribed?: number;
  instructions?: string;
}

export interface PrescriptionResponse {
  id: string;
  consultation_id: string;
  visit_id: string;
  pharmacy_catalog_item_id?: string | null;
  drug_name: string;
  dosage: string;
  frequency: string;
  duration: string;
  quantity_prescribed: number;
  quantity_dispensed_total: number;
  quantity_remaining: number;
  instructions: string | null;
  status: 'ISSUED' | 'DISPENSED' | 'CANCELLED' | 'EXTERNALLY_FULFILLED';
  prescribed_by: string;
  dispensed_by: string | null;
  issued_at: string;
  dispensed_at: string | null;
  cancelled_at: string | null;
  workflow_status:
    | 'ASSIGNED'
    | 'AWAITING_PAYMENT_CLEARANCE'
    | 'READY_TO_DISPENSE'
    | 'IN_DISPENSE'
    | 'DISPENSED'
    | 'REASSIGNED'
    | 'CANCELLED'
    | 'EXTERNALLY_FULFILLED';
  billing_item_id?: string | null;
  billing_status?: string | null;
  assigned_dispensing_unit_id?: string | null;
  assigned_dispensing_unit_name?: string | null;
  assigned_cashier_pay_point_id?: string | null;
  assigned_cashier_pay_point_name?: string | null;
  exception_authorization_type?:
    | 'NONE'
    | 'NHIS_COVERED'
    | 'EMERGENCY_OVERRIDE'
    | 'HOD_AUTHORIZED_OVERRIDE';
  payment_cleared?: boolean | null;
  externally_fulfilled_at?: string | null;
}

export const prescriptionService = {
  async issuePrescription(
    payload: PrescriptionCreateRequest
  ): Promise<PrescriptionResponse> {
    const response = await client.post('/v1/prescriptions', payload);
    return response.data;
  },
};
