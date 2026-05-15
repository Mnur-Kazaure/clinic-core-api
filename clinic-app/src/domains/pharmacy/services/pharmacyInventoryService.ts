import client from '@/api/client';

export type InventoryMode = 'EDITABLE' | 'READ_ONLY';
export type StockFilter =
  | 'ALL'
  | 'ACTIVE'
  | 'INACTIVE'
  | 'AVAILABLE'
  | 'LOW_STOCK'
  | 'OUT_OF_STOCK';

export interface PharmacyInventoryItemDTO {
  id: string;
  clinic_id: string;
  generic_name: string;
  brand_name: string | null;
  dosage_form: string;
  strength: string | null;
  unit_of_measure: string;
  selling_price_minor: number;
  currency: string;
  stock_quantity: number;
  low_stock_threshold: number;
  lifecycle_status: 'ACTIVE' | 'INACTIVE';
  last_restocked_at: string | null;
  created_by: string;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface PharmacyInventoryListResponse {
  data: PharmacyInventoryItemDTO[];
  total: number;
  page: number;
  limit: number;
}

export interface PharmacyStockMovementDTO {
  id: string;
  clinic_id: string;
  inventory_item_id: string;
  actor_id: string;
  actor_name: string | null;
  movement_type:
    | 'RESTOCK'
    | 'DISPENSE'
    | 'ADJUSTMENT'
    | 'PRICE_UPDATE'
    | 'ACTIVATED'
    | 'INACTIVATED';
  quantity_delta: number;
  stock_before: number;
  stock_after: number;
  note: string | null;
  reference_type: string | null;
  reference_id: string | null;
  occurred_at: string;
}

export interface PharmacyStockMovementListResponse {
  data: PharmacyStockMovementDTO[];
  total: number;
  limit: number;
  offset: number;
}

export interface PharmacyAccessModeResponse {
  inventory_mode: InventoryMode;
  changed_by: string | null;
  changed_by_name: string | null;
  changed_at: string | null;
}

export interface PharmacyOverviewResponse {
  total_drugs: number;
  low_stock: number;
  out_of_stock: number;
  todays_dispenses: number;
  inventory_value_minor: number;
  currency: string;
  alerts: string[];
  inventory_health: {
    available: number;
    low_stock: number;
    out_of_stock: number;
    inactive: number;
  };
  recent_movements: PharmacyStockMovementDTO[];
  top_dispensed_drugs: Array<{
    drug_name: string;
    dispensed_count: number;
  }>;
  access_mode: PharmacyAccessModeResponse;
}

export interface PharmacyInventoryCreatePayload {
  generic_name: string;
  brand_name?: string | null;
  dosage_form: string;
  strength?: string | null;
  unit_of_measure: string;
  selling_price_minor: number;
  currency: string;
  initial_stock: number;
  low_stock_threshold: number;
  lifecycle_status: 'ACTIVE' | 'INACTIVE';
}

export interface PharmacyInventoryUpdatePayload {
  generic_name?: string;
  brand_name?: string | null;
  dosage_form?: string;
  strength?: string | null;
  unit_of_measure?: string;
  selling_price_minor?: number;
  currency?: string;
  low_stock_threshold?: number;
  lifecycle_status?: 'ACTIVE' | 'INACTIVE';
  note?: string | null;
}

export const pharmacyInventoryService = {
  async getOverview(): Promise<PharmacyOverviewResponse> {
    const response = await client.get('/v1/pharmacy/inventory/overview');
    return response.data;
  },

  async listInventory(params: {
    search?: string;
    stock_filter?: StockFilter;
    page?: number;
    limit?: number;
  }): Promise<PharmacyInventoryListResponse> {
    const response = await client.get('/v1/pharmacy/inventory', {
      params,
    });
    return response.data;
  },

  async getItem(itemId: string): Promise<PharmacyInventoryItemDTO> {
    const response = await client.get(`/v1/pharmacy/inventory/${itemId}`);
    return response.data;
  },

  async createItem(
    payload: PharmacyInventoryCreatePayload
  ): Promise<PharmacyInventoryItemDTO> {
    const response = await client.post('/v1/pharmacy/inventory', payload);
    return response.data;
  },

  async updateItem(
    itemId: string,
    payload: PharmacyInventoryUpdatePayload
  ): Promise<PharmacyInventoryItemDTO> {
    const response = await client.put(`/v1/pharmacy/inventory/${itemId}`, payload);
    return response.data;
  },

  async restockItem(
    itemId: string,
    payload: { quantity: number; note?: string | null }
  ): Promise<PharmacyInventoryItemDTO> {
    const response = await client.post(
      `/v1/pharmacy/inventory/${itemId}/restock`,
      payload
    );
    return response.data;
  },

  async listMovements(
    itemId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<PharmacyStockMovementListResponse> {
    const response = await client.get(`/v1/pharmacy/inventory/${itemId}/movements`, {
      params,
    });
    return response.data;
  },

  async getAccessMode(): Promise<PharmacyAccessModeResponse> {
    const response = await client.get('/v1/pharmacy/inventory/access-mode');
    return response.data;
  },
};
