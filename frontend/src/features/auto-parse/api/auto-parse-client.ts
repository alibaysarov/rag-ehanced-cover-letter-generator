import { authApi } from '@/api/client';
import { API_BASE_URL } from '@/api/client';
import { TokenManager } from '@/features/auth';
import type { ParsingJob, AutoParsedJob } from '../types';

export const autoParseApi = {
  async startParse(query: string): Promise<{ parsing_job_id: number }> {
    const res = await authApi.post<{ parsing_job_id: number }>(
      '/auto-parse/start',
      { query },
    );
    return res.data;
  },

  async getStatus(jobId: number): Promise<ParsingJob> {
    const res = await authApi.get<ParsingJob>(`/auto-parse/status/${jobId}`);
    return res.data;
  },

  async getVacancies(jobId: number): Promise<AutoParsedJob[]> {
    const res = await authApi.get<AutoParsedJob[]>(
      `/auto-parse/jobs/${jobId}/vacancies`,
    );
    return res.data;
  },

  async getHistory(): Promise<ParsingJob[]> {
    const res = await authApi.get<ParsingJob[]>('/auto-parse/history');
    return res.data;
  },

  async markApplied(vacancyId: number, letterText?: string): Promise<AutoParsedJob> {
    const res = await authApi.patch<AutoParsedJob>(`/auto-parse/vacancies/${vacancyId}/applied`, {
      letter_text: letterText ?? '',
    });
    return res.data;
  },

  // EventSource cannot set Authorization headers, so the JWT is passed as a
  // query parameter. The backend must accept ?token=<jwt> for this endpoint.
  createEventSource(jobId: number): EventSource {
    const token = TokenManager.getAccessToken() ?? '';
    const url = `${API_BASE_URL}/auto-parse/stream/${jobId}?token=${encodeURIComponent(token)}`;
    return new EventSource(url);
  },
};
