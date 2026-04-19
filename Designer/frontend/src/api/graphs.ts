import http, { unwrap } from './client'
import type {
  ForestSnapshot,
  GraphInfo,
  GraphVersionMeta,
  ValidationReport,
} from '@/types'

export const graphsApi = {
  list: () => unwrap<GraphInfo[]>(http.get('/graphs')),

  detail: (id: string) => unwrap<GraphInfo>(http.get(`/graphs/${id}`)),

  create: (body: { name: string; description?: string }) =>
    unwrap<{ graph_id: string }>(http.post('/graphs', body)),

  updateMeta: (id: string, body: { name?: string; description?: string }) =>
    unwrap<{ ok: boolean }>(http.put(`/graphs/${id}`, body)),

  remove: (id: string) => http.delete(`/graphs/${id}`),

  listVersions: (id: string) =>
    unwrap<GraphVersionMeta[]>(http.get(`/graphs/${id}/versions`)),

  getVersion: (id: string, version: number) =>
    unwrap<ForestSnapshot>(http.get(`/graphs/${id}/versions/${version}`)),

  saveVersion: (
    id: string,
    body: { snapshot: ForestSnapshot; commit_message?: string; parent_version_id?: string | null },
  ) => unwrap<{ version_id: string }>(http.post(`/graphs/${id}/versions`, body)),

  getDraft: (id: string) =>
    unwrap<ForestSnapshot | null>(http.get(`/graphs/${id}/draft`)),

  saveDraft: (id: string, snapshot: ForestSnapshot) =>
    unwrap<{ ok: boolean }>(http.put(`/graphs/${id}/draft`, snapshot)),

  validate: (snapshot: ForestSnapshot) =>
    unwrap<ValidationReport>(http.post('/graphs/_validate', snapshot)),

  diff: (id: string, v1: number, v2: number) =>
    unwrap<Record<string, unknown>>(
      http.get(`/graphs/${id}/versions/_diff`, { params: { v1, v2 } }),
    ),
}
