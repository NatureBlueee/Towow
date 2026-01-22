import { apiClient } from './client';
import type { DemandSubmitRequest, DemandSubmitResponse } from '../types';

export const demandApi = {
  submit: async (data: DemandSubmitRequest): Promise<DemandSubmitResponse> => {
    const response = await apiClient.post<DemandSubmitResponse>('/api/v1/demand/submit', data);
    return response.data;
  },

  getStatus: async (demandId: string) => {
    const response = await apiClient.get(`/api/v1/demand/${demandId}/status`);
    return response.data;
  },

  getHistory: async (page = 1, pageSize = 10) => {
    const response = await apiClient.get('/api/v1/demands', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },
};
