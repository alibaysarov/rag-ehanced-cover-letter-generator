import { authApi } from '@/api/client';
import type { ParserDetail, ParserInput, ParserListResponse } from './types';
export interface PreviewResponse { resolved_url: string; fetch_mode: 'http' | 'playwright'; stage: 'list' | 'detail' | 'pagination'; result: unknown; warnings: string[]; timing_ms: number }

export const parserApi = {
  async list(page: number, pageSize: number): Promise<ParserListResponse> {
    const response = await authApi.get<ParserListResponse>('/parsers', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },
  async detail(id: number): Promise<ParserDetail> {
    return (await authApi.get<ParserDetail>(`/parsers/${id}`)).data;
  },
  async create(data: ParserInput): Promise<ParserDetail> {
    return (await authApi.post<ParserDetail>('/parsers', data)).data;
  },
  async update(id: number, data: ParserInput, version: number): Promise<ParserDetail> {
    return (await authApi.put<ParserDetail>(`/parsers/${id}`, { ...data, version })).data;
  },
  async remove(id: number): Promise<void> {
    await authApi.delete(`/parsers/${id}`);
  },
  async preview(payload: { parser: ParserInput; stage: 'list' | 'detail' | 'pagination'; search_text?: string; page?: number; url?: string }): Promise<PreviewResponse> {
    return (await authApi.post<PreviewResponse>('/parsers/preview', payload)).data;
  },
};
