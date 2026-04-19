/** 森林 JSON(与后端 ForestSnapshotDTO 一一对应) */

export interface NodeInstanceDTO {
  instance_id: string
  template_id: string
  template_version: number
  /** 保存时由后端 freeze_snapshot 填写;前端 draft 可不传 */
  template_snapshot?: Record<string, unknown> | null
  instance_name: string
  field_values: Record<string, unknown>
  bundle_id?: string | null
}

export interface EdgeDTO {
  edge_id: string
  /** 注意 from/to 是 alias,后端原字段名是 src/dst */
  from: string
  to: string
  edge_semantic: string
}

export interface BundleDTO {
  bundle_id: string
  name: string
  description?: string
  node_instance_ids: string[]
}

export interface ForestSnapshot {
  bundles: BundleDTO[]
  node_instances: NodeInstanceDTO[]
  edges: EdgeDTO[]
  metadata?: Record<string, unknown>
}

export interface GraphInfo {
  id: string
  name: string
  description: string
  status: 'draft' | 'validating' | 'validated' | 'failed'
  latest_version_id: string | null
}

export interface GraphVersionMeta {
  id: string
  version_number: number
  commit_message: string
  parent_version_id: string | null
  created_at: string
}

export interface ValidationReport {
  ok: boolean
  errors: Array<{ code: string; message: string; extra?: Record<string, unknown> }>
  warnings: Array<{ code: string; instance_id?: string }>
}
