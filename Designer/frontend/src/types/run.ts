export type PipelineVariant = 'phase1_only' | 'up_to_phase2' | 'full'
export type RunStatus = 'pending' | 'running' | 'success' | 'failed' | 'cancelled'
export type Verdict = 'valid' | 'invalid' | 'inconclusive' | null

export interface ScenarioInput {
  name: string
  input_json: Record<string, unknown>
  expected_output: Record<string, unknown>
  tables?: Record<string, unknown[]>
  description?: string
  target_root?: string | null
}

export interface RunTriggerReq {
  graph_version_id: string
  scenarios: ScenarioInput[]
  options?: { variant?: PipelineVariant; [k: string]: unknown }
}

export interface RunSummary {
  id: string
  graph_version_id: string
  status: RunStatus
  final_verdict: Verdict
  phase1_verdict: Verdict
  started_at: string | null
  finished_at: string | null
  created_at: string
}

export interface RunEvent {
  type: string
  run_id: string
  ts: string
  phase?: number | null
  step_id?: string | null
  node_name?: string | null
  handler_name?: string | null
  payload?: Record<string, unknown> | null
}
