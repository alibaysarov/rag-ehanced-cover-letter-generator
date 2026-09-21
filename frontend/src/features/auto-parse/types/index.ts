export type ParsingJobStatus = 'pending' | 'running' | 'done' | 'failed';
export type GenerationMode = 'ai' | 'template';

export interface ParsingJob {
  id: number;
  query: string;
  status: ParsingJobStatus;
  saved_count: number;
  total_found: number;
  created_at: string;
  finished_at: string | null;
  error: string | null;
  generation_mode: GenerationMode;
  auto_generation_started_at?: string | null;
  auto_generation_error?: string | null;
}

export interface AutoParsedJob {
  id: number;
  parsing_job_id: number | null;
  vacancy_id: string | null;
  url: string;
  web_site: string | null;
  job_title: string;
  job_text: string;
  is_applied: boolean;
  is_viewed: boolean;
  is_generated: boolean;
  cover_letter_text: string | null;
  created_at: string;
}

export interface ParsingVacancySavedEvent {
  type: 'parsing.vacancy_saved';
  parsing_job_id: number;
  site_key: string;
  vacancy: AutoParsedJob;
}
