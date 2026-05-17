export interface LetterFromUrlRequest {
  url: string;
  source_id: number;
  file?: File;
}

export interface LetterFromTextRequest {
  name: string;
  description: string;
  source_id: number;
  file?: File;
}

export interface CVUploadRequest {
  file: File;
}

export interface CVUploadResponse {
  success: boolean;
  message: string;
  source_id: number;
  data?: {
    filename: string;
    file_size: number;
    source_id: number;
  };
  errors?: string[];
}

export interface LetterResponse {
  success: boolean;
  message: string;
  data?: {
    url: string;
    letter_content: string;
    source_id: number;
  };
  errors?: string[];
}

export interface StreamLetterFromUrlRequest {
  url: string;
}

export interface StreamLetterFromTextRequest {
  name: string;
  description: string;
  lang?: string;
}

export type StreamStatus = 'idle' | 'parsing' | 'streaming' | 'done' | 'error';

export interface StreamChunk {
  delta?: string;
  status?: '__PARSING__' | '__READY__';
  error?: string;
}

/** ISO language name displayed to user and sent to API */
export interface Language {
  code: string;
  label: string;
  apiName: string;
}

export const LANGUAGES: Language[] = [
  { code: 'en', label: 'English', apiName: 'English' },
  { code: 'ru', label: 'Русский', apiName: 'Russian' },
  { code: 'de', label: 'Deutsch', apiName: 'German' },
  { code: 'fr', label: 'Français', apiName: 'French' },
  { code: 'es', label: 'Español', apiName: 'Spanish' },
  { code: 'pt', label: 'Português', apiName: 'Portuguese' },
  { code: 'it', label: 'Italiano', apiName: 'Italian' },
  { code: 'pl', label: 'Polski', apiName: 'Polish' },
  { code: 'uk', label: 'Українська', apiName: 'Ukrainian' },
  { code: 'tr', label: 'Türkçe', apiName: 'Turkish' },
  { code: 'nl', label: 'Nederlands', apiName: 'Dutch' },
  { code: 'zh', label: '中文', apiName: 'Chinese (Simplified)' },
  { code: 'ar', label: 'العربية', apiName: 'Arabic' },
];

export interface TranslateRequest {
  text: string;
  target_language: string;
}
