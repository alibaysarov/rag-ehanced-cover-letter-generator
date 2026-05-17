export type ParsingJobStatus = 'pending' | 'running' | 'done' | 'failed';

export interface ParsingJob {
  id: number;
  query: string;
  status: ParsingJobStatus;
  saved_count: number;
  total_found: number;
  created_at: string;
  finished_at: string | null;
}

export interface AutoParsedJob {
  id: number;
  vacancy_id: string;
  url: string;
  job_title: string;
  job_text: string;
  is_applied: boolean;
  is_viewed: boolean;
  is_generated: boolean;
  cover_letter_text: string | null;
  created_at: string;
}
