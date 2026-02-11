import client from '@/api/client';

export interface ChargeCatalogItem {
  id: string;
  code: string;
  name: string;
  category: string;
  default_amount_minor: number;
  currency: string;
  active: boolean;
  usage_today_count: number;
  usage_today_minor: number;
}

export interface ChargeCatalogCreateRequest {
  code: string;
  name: string;
  category: string;
  default_amount_minor: number;
  currency: string;
  active: boolean;
}

export interface ChargeCatalogUpdateRequest {
  name?: string;
  category?: string;
  default_amount_minor?: number;
  currency?: string;
  active?: boolean;
}

export const chargeCatalogService = {
  async list(): Promise<ChargeCatalogItem[]> {
    const response = await client.get('/v1/admin/charge-catalog');
    return response.data;
  },
  async create(payload: ChargeCatalogCreateRequest): Promise<ChargeCatalogItem> {
    const response = await client.post('/v1/admin/charge-catalog', payload);
    return response.data;
  },
  async update(id: string, payload: ChargeCatalogUpdateRequest): Promise<ChargeCatalogItem> {
    const response = await client.patch(`/v1/admin/charge-catalog/${id}`, payload);
    return response.data;
  },
};
