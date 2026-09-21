export type TemplateCase =
  | 'no_portfolio'
  | 'relevant_domain'
  | 'partial_match'
  | 'no_relevant_projects';
export type PhraseType =
  | 'opening'
  | 'experience_bridge'
  | 'portfolio_intro'
  | 'stack_summary'
  | 'closing'
  | 'custom';
export type TemplateStatus = 'draft' | 'active' | 'archived';
export type NodeKind = 'phrase' | 'projects';

export interface LetterPhrase {
  id: number;
  type: PhraseType;
  text: string;
  is_active: boolean;
  used_in_templates: number;
  created_at: string;
  updated_at: string;
}
export interface Page<T> { items: T[]; page: number; page_size: number; total: number }
export interface Position { x: number; y: number }
export interface TemplateNodeDto {
  id: string; node_kind: NodeKind; phrase_id: number | null; position: Position;
  phrase?: LetterPhrase | null;
}
export interface TemplateEdgeDto {
  id: string; source_node_id: string; target_node_id: string; branch_order: number;
}
export interface TemplateSummary {
  id: number; name: string; case: TemplateCase; status: TemplateStatus;
  root_node_id: string | null; version: number; has_projects_node: boolean;
  nodes_count: number; edges_count: number; created_at: string; updated_at: string;
}
export interface CoverLetterTemplate extends Omit<TemplateSummary, 'has_projects_node' | 'nodes_count' | 'edges_count'> {
  nodes: TemplateNodeDto[]; edges: TemplateEdgeDto[];
}
export interface TemplatePayload {
  name: string; case: TemplateCase; version?: number; confirm_without_projects: boolean;
  root_node_id: string | null; nodes: TemplateNodeDto[]; edges: TemplateEdgeDto[];
}
export interface ConstructorErrorDetail { code: string; reason?: string; errors?: Array<Record<string, unknown>> }
export interface PreviewResult { detected_case: TemplateCase; template_case: TemplateCase; text: string; node_path: string[]; warning?: string | null }
