export interface FormatUrlConfig {
  url_template: string;
  query_params: Record<string, string>;
}

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
};
