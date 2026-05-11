import client from '@/api/client';

export type PharmacyCatalogLifecycleStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'AWAITING_CMD_APPROVAL'
  | 'CMD_APPROVED'
  | 'PRICING_PENDING'
  | 'PRICED'
  | 'ACTIVE'
  | 'REJECTED'
  | 'DEACTIVATED';

export type PharmacyPricingStatus = 'NOT_CONFIGURED' | 'PRICED' | 'ACTIVE' | 'INACTIVE';
export type PharmacyInventoryClassification = 'DRUG' | 'CONSUMABLE' | 'EQUIPMENT';
export type PharmacyInventoryTrackingMode = 'LOT_TRACKED' | 'QUANTITY_ONLY' | 'SERIALIZED';

export interface PharmacyCatalogRegistryRow {
  id: string;
  catalog_code: string;
  generic_name: string;
  brand_name?: string | null;
  strength?: string | null;
  dosage_form: string;
  dispense_unit: string;
  classification: PharmacyInventoryClassification;
  tracking_mode: PharmacyInventoryTrackingMode;
  requires_expiry: boolean;
  lifecycle_status: PharmacyCatalogLifecycleStatus;
  billing_status: PharmacyPricingStatus;
  active: boolean;
  justification: string;
  requested_by: string;
  requested_by_name?: string | null;
  submitted_by?: string | null;
  submitted_by_name?: string | null;
  submitted_at?: string | null;
  cmd_reviewed_by?: string | null;
  cmd_reviewed_by_name?: string | null;
  cmd_reviewed_at?: string | null;
  cmd_review_note?: string | null;
  priced_by?: string | null;
  priced_by_name?: string | null;
  priced_at?: string | null;
  activated_by?: string | null;
  activated_by_name?: string | null;
  activated_at?: string | null;
  deactivated_by?: string | null;
  deactivated_by_name?: string | null;
  deactivated_at?: string | null;
  current_price_minor?: number | null;
  current_currency?: string | null;
  charge_code?: string | null;
  effective_date?: string | null;
}

export interface PharmacyPricingConfig {
  id: string;
  catalog_item_id: string;
  charge_code: string;
  unit_price_minor: number;
  currency: string;
  effective_date: string;
  status: PharmacyPricingStatus;
  active: boolean;
  configured_by: string;
  configured_by_name?: string | null;
  configured_at?: string | null;
  activated_by?: string | null;
  activated_by_name?: string | null;
  activated_at?: string | null;
  deactivated_by?: string | null;
  deactivated_by_name?: string | null;
  deactivated_at?: string | null;
}

export interface PharmacyCatalogGovernanceDetail {
  item: PharmacyCatalogRegistryRow;
  pricing?: PharmacyPricingConfig | null;
}

export interface PharmacyCatalogRequestCreatePayload {
  generic_name: string;
  brand_name?: string | null;
  strength?: string | null;
  dosage_form: string;
  dispense_unit: string;
  classification: PharmacyInventoryClassification;
  tracking_mode: PharmacyInventoryTrackingMode;
  requires_expiry: boolean;
  justification: string;
  submit_now?: boolean;
}

export interface PharmacyCatalogRequestReviewPayload {
  decision: 'APPROVE' | 'REJECT';
  note?: string | null;
}

export interface PharmacyPricingConfigUpsertPayload {
  charge_code: string;
  unit_price_minor: number;
  currency: string;
  effective_date: string;
  activate?: boolean;
}

export interface PharmacyActiveCatalogItem {
  id: string;
  catalog_code: string;
  generic_name: string;
  brand_name?: string | null;
  strength?: string | null;
  dosage_form: string;
  dispense_unit: string;
  classification: PharmacyInventoryClassification;
  tracking_mode: PharmacyInventoryTrackingMode;
  requires_expiry: boolean;
  charge_code: string;
  unit_price_minor: number;
  currency: string;
  display_name: string;
}

export const pharmacyCatalogGovernanceService = {
  async listHodCatalogRequests(): Promise<PharmacyCatalogRegistryRow[]> {
    const response = await client.get('/v1/pharmacy-hod/catalog-requests');
    return response.data;
  },

  async createHodCatalogRequest(
    payload: PharmacyCatalogRequestCreatePayload
  ): Promise<PharmacyCatalogRegistryRow> {
    const response = await client.post('/v1/pharmacy-hod/catalog-requests', payload);
    return response.data;
  },

  async listCmdCatalogRequests(): Promise<PharmacyCatalogRegistryRow[]> {
    const response = await client.get('/v1/pharmacy-cmd/catalog-requests');
    return response.data;
  },

  async reviewCmdCatalogRequest(
    itemId: string,
    payload: PharmacyCatalogRequestReviewPayload
  ): Promise<PharmacyCatalogRegistryRow> {
    const response = await client.post(`/v1/pharmacy-cmd/catalog-requests/${itemId}/review`, payload);
    return response.data;
  },

  async listAccountantPricingQueue(): Promise<PharmacyCatalogRegistryRow[]> {
    const response = await client.get('/v1/accountant/pharmacy-pricing');
    return response.data;
  },

  async upsertPricing(
    itemId: string,
    payload: PharmacyPricingConfigUpsertPayload
  ): Promise<PharmacyCatalogGovernanceDetail> {
    const response = await client.post(`/v1/accountant/pharmacy-pricing/${itemId}`, payload);
    return response.data;
  },

  async listAdminCatalogRegistry(): Promise<PharmacyCatalogRegistryRow[]> {
    const response = await client.get('/v1/admin/pharmacy-catalog');
    return response.data;
  },

  async listActiveCatalogItems(): Promise<PharmacyActiveCatalogItem[]> {
    const response = await client.get('/v1/prescriptions/catalog/active');
    return response.data;
  },
};
