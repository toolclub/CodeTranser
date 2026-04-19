import http, { unwrap } from './client'
import type {
  MetaTemplate,
  NodeTemplateCard,
  NodeTemplateCreate,
  NodeTemplateOut,
} from '@/types'

export const templatesApi = {
  listCards: (params?: { category?: string; scope?: 'global' | 'private' | 'all' }) =>
    unwrap<NodeTemplateCard[]>(http.get('/node-templates', { params })),

  getCard: (id: string) =>
    unwrap<NodeTemplateCard>(http.get(`/node-templates/${id}`)),

  createPrivate: (body: NodeTemplateCreate) =>
    unwrap<{ template_id: string }>(http.post('/node-templates', body)),

  // Admin / 作者
  getFull: (id: string, version?: number) =>
    unwrap<NodeTemplateOut>(
      http.get(`/admin/node-templates/${id}`, { params: version ? { version } : {} }),
    ),

  listVersions: (id: string) =>
    unwrap<Array<{ version_number: number; change_note: string; created_at: string }>>(
      http.get(`/admin/node-templates/${id}/versions`),
    ),

  activateVersion: (id: string, ver: number) =>
    unwrap<{ ok: boolean }>(
      http.post(`/admin/node-templates/${id}/versions/${ver}/activate`),
    ),

  createGlobal: (body: NodeTemplateCreate) =>
    unwrap<{ template_id: string }>(http.post('/admin/node-templates', body)),

  fork: (id: string) =>
    unwrap<{ template_id: string }>(http.post(`/admin/node-templates/${id}/fork`)),

  update: (id: string, body: Omit<NodeTemplateCreate, 'name' | 'scope'>) =>
    unwrap<{ version_number: number }>(http.put(`/admin/node-templates/${id}`, body)),

  simulate: (
    id: string,
    body: { field_values: Record<string, unknown>; input_json: Record<string, unknown>; tables?: Record<string, unknown[]> },
  ) =>
    unwrap<{
      output_json: Record<string, unknown>
      engine_used: string
      duration_ms: number
      llm_call_id: string | null
    }>(http.post(`/admin/node-templates/${id}/simulate`, body)),
}

export const metaTemplateApi = {
  get: () => unwrap<MetaTemplate>(http.get('/admin/meta-node-template')),
  update: (content: MetaTemplate, note = '') =>
    unwrap<{ ok: boolean }>(http.put('/admin/meta-node-template', { content, note })),
}
