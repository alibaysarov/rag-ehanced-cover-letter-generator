export interface FormatUrlConfig {
  url_template: string;
  query_params: Record<string, string>;
}
export type ExtractionEngine = 'legacy_js' | 'selectors_v1';
export type FetchMode = 'http' | 'playwright';
export interface RequestConfig { headers: Record<string, string>; timeout_seconds: number; max_retries: number; retry_base_delay_seconds: number; playwright: { wait_for_selector: string | null; wait_until: 'domcontentloaded' | 'load' | 'networkidle'; scroll_to_bottom: boolean; post_load_delay_ms: number } }
export interface SelectorRule { source: { kind: 'selector'; selectors: string[]; extract: 'text' | 'attribute'; attribute?: string; absolute_url?: boolean } | { kind: 'field'; field: string }; required: boolean; normalize: { strip: boolean; collapse_whitespace: boolean }; transforms: Array<{ kind: 'regex'; pattern: string; group: number }> }
export interface SelectorExtractionConfig { schema_version: 1; list: { item_selector: string; fields: Record<'title' | 'link' | 'vacancy_id', SelectorRule> }; detail: { fields: { job_title: SelectorRule; job_text: SelectorRule; company_name?: SelectorRule } }; pagination: { enabled: boolean; selectors: string[]; extract: 'text' | 'attribute'; attribute?: string; transforms: Array<{ kind: 'regex'; pattern: string; group: number }> } | null }

export interface ParserInput {
  name: string;
  base_url: string;
  single_url: string;
  has_pagination: boolean;
  evaluate_vacancy_list: string;
  evaluate_vacancy_page: string;
  evaluate_pagination: string | null;
  format_url: FormatUrlConfig;
  pagination_start: number;
  max_pages: number;
  extraction_engine: ExtractionEngine;
  fetch_mode: FetchMode;
  request_config: RequestConfig;
  extraction_config: SelectorExtractionConfig | null;
}

export interface ParserDetail extends ParserInput {
  id: number;
  site_key: string;
  version: number;
  created_at: string;
  updated_at: string;
  is_in_use: boolean;
  can_delete: boolean;
}

export type ParserListItem = Pick<
  ParserDetail,
  | 'id'
  | 'name'
  | 'site_key'
  | 'base_url'
  | 'has_pagination'
  | 'version'
  | 'created_at'
  | 'updated_at'
  | 'is_in_use'
  | 'can_delete'
>;

export interface ParserListResponse {
  items: ParserListItem[];
  total: number;
  page: number;
  page_size: number;
}

export const emptyParser: ParserInput = {
  name: '',
  base_url: '',
  single_url: '',
  has_pagination: false,
  evaluate_vacancy_list: '',
  evaluate_vacancy_page: '',
  evaluate_pagination: '',
  format_url: { url_template: '{base_url}', query_params: { text: '{text}' } },
  pagination_start: 0,
  max_pages: 5,
  extraction_engine: 'selectors_v1',
  fetch_mode: 'http',
  request_config: { headers: {}, timeout_seconds: 20, max_retries: 2, retry_base_delay_seconds: 0.5, playwright: { wait_for_selector: null, wait_until: 'domcontentloaded', scroll_to_bottom: false, post_load_delay_ms: 0 } },
  extraction_config: { schema_version: 1, list: { item_selector: '', fields: {
    title: { source: { kind: 'selector', selectors: [''] , extract: 'text' }, required: true, normalize: { strip: true, collapse_whitespace: true }, transforms: [] },
    link: { source: { kind: 'selector', selectors: [''], extract: 'attribute', attribute: 'href', absolute_url: true }, required: true, normalize: { strip: true, collapse_whitespace: false }, transforms: [] },
    vacancy_id: { source: { kind: 'field', field: 'link' }, required: true, normalize: { strip: true, collapse_whitespace: false }, transforms: [{ kind: 'regex', pattern: '', group: 1 }] },
  } }, detail: { fields: {
    job_title: { source: { kind: 'selector', selectors: [''], extract: 'text' }, required: true, normalize: { strip: true, collapse_whitespace: true }, transforms: [] },
    job_text: { source: { kind: 'selector', selectors: [''], extract: 'text' }, required: true, normalize: { strip: true, collapse_whitespace: true }, transforms: [] },
  } }, pagination: null },
};
