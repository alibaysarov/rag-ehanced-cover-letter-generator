import { describe, expect, it } from 'vitest';
import { apiGraphToFlow, flowGraphToApi } from './graphAdapter';
import type { CoverLetterTemplate } from './types';

describe('letter constructor graph adapter', () => {
  it('round-trips API graph without UI-only node data', () => {
    const template: CoverLetterTemplate = {
      id: 1,
      name: 'Example',
      case: 'partial_match',
      status: 'draft',
      root_node_id: '00000000-0000-0000-0000-000000000001',
      version: 2,
      created_at: '2026-09-21T10:00:00Z',
      updated_at: '2026-09-21T10:00:00Z',
      nodes: [{
        id: '00000000-0000-0000-0000-000000000001',
        node_kind: 'phrase',
        phrase_id: 9,
        position: { x: 10, y: 20 },
        phrase: {
          id: 9, type: 'opening', text: 'Hello [[job_title]]', is_active: true,
          used_in_templates: 1, created_at: '2026-09-21T10:00:00Z', updated_at: '2026-09-21T10:00:00Z',
        },
      }, {
        id: '00000000-0000-0000-0000-000000000002', node_kind: 'projects',
        phrase_id: null, position: { x: 30, y: 40 }, phrase: null,
      }],
      edges: [{
        id: '00000000-0000-0000-0000-000000000003',
        source_node_id: '00000000-0000-0000-0000-000000000001',
        target_node_id: '00000000-0000-0000-0000-000000000002', branch_order: 0,
      }],
    };
    const flow = apiGraphToFlow(template);
    const api = flowGraphToApi(flow.nodes, flow.edges, template.root_node_id);
    expect(api.nodes).toEqual(template.nodes.map(({ phrase: _phrase, ...node }) => node));
    expect(api.edges).toEqual(template.edges);
    expect(api.nodes[0]).not.toHaveProperty('data');
  });
});
