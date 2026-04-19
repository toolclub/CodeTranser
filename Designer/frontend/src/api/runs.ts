import http, { unwrap } from './client'
import type { RunSummary, RunTriggerReq } from '@/types'

/** Ch10 尚未实装;前端先预留接口,接入时替换 */
export const runsApi = {
  list: () => unwrap<RunSummary[]>(http.get('/runs')),

  detail: (id: string) => unwrap<RunSummary>(http.get(`/runs/${id}`)),

  trigger: (body: RunTriggerReq) =>
    unwrap<{ run_id: string; status: string }>(http.post('/runs', body)),

  getCodeDiff: (id: string) =>
    unwrap<{ files: Record<string, { before: string; after: string }> }>(
      http.get(`/runs/${id}/code-snapshot/diff`),
    ),
}
