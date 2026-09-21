import { authApi } from '@/api/client';
import type {
  CoverLetterTemplate, LetterPhrase, Page, PhraseType, PreviewResult, TemplateCase,
  TemplatePayload, TemplateStatus, TemplateSummary,
} from './types';

export const letterConstructorApi = {
  async phrases(params: { q?: string; type?: PhraseType; is_active?: boolean; page: number; page_size: number }) {
    return (await authApi.get<Page<LetterPhrase>>('/letter-phrases', { params })).data;
  },
  async createPhrase(data: Pick<LetterPhrase, 'type' | 'text' | 'is_active'>) {
    return (await authApi.post<LetterPhrase>('/letter-phrases', data)).data;
  },
  async updatePhrase(id: number, data: Partial<Pick<LetterPhrase, 'type' | 'text' | 'is_active'>>) {
    return (await authApi.patch<LetterPhrase>(`/letter-phrases/${id}`, data)).data;
  },
  async deletePhrase(id: number) { await authApi.delete(`/letter-phrases/${id}`); },
  async templates(params: { q?: string; case?: TemplateCase; status?: TemplateStatus; page: number; page_size: number }) {
    return (await authApi.get<Page<TemplateSummary>>('/cover-letter-templates', { params })).data;
  },
  async template(id: number) { return (await authApi.get<CoverLetterTemplate>(`/cover-letter-templates/${id}`)).data; },
  async createTemplate(data: TemplatePayload) { return (await authApi.post<CoverLetterTemplate>('/cover-letter-templates', data)).data; },
  async updateTemplate(id: number, data: TemplatePayload) { return (await authApi.put<CoverLetterTemplate>(`/cover-letter-templates/${id}`, data)).data; },
  async activateTemplate(id: number, version: number, confirm_without_projects = false) {
    return (await authApi.post<CoverLetterTemplate>(`/cover-letter-templates/${id}/activate`, { version, confirm_without_projects })).data;
  },
  async deleteTemplate(id: number) { await authApi.delete(`/cover-letter-templates/${id}`); },
  async previewTemplate(id: number, vacancy_id: number) { return (await authApi.post<PreviewResult>(`/cover-letter-templates/${id}/preview`, { vacancy_id })).data; },
};
