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

export interface GeneralOption {
  value: string;
  name: string;
}

export interface CVOptionsResponse {
  data:{
    options:GeneralOption[]
  }
}
