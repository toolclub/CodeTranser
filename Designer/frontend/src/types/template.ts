export type Engine = 'pure_python' | 'llm' | 'hybrid'
export type Scope = 'global' | 'private'
export type TemplateStatus = 'draft' | 'active' | 'deprecated'

export interface EdgeSemantic {
  field: string
  description?: string
}

export interface CodeHints {
  style_hints?: string[]
  forbidden?: string[]
  example_fragment?: string
}

export interface JsonSimulatorSpec {
  engine: Engine
  python_impl?: string | null
  llm_fallback?: boolean
}

export interface NodeTemplateDefinition {
  description: string[]
  input_schema: Record<string, unknown>
  output_schema: Record<string, unknown>
  simulator: JsonSimulatorSpec
  edge_semantics?: EdgeSemantic[]
  code_hints?: CodeHints
  extensions?: Record<string, unknown>
}

/** 后端 NodeTemplateCardDTO — 前端画布的投影 */
export interface NodeTemplateCard {
  id: string
  name: string
  display_name: string
  category: string
  current_version: number
  input_schema: Record<string, unknown>
  edge_semantics: EdgeSemantic[]
  extensions?: Record<string, unknown>
}

/** 后端 NodeTemplateOutDTO — admin/作者完整版 */
export interface NodeTemplateOut {
  id: string
  name: string
  display_name: string
  category: string
  scope: Scope
  status: TemplateStatus
  current_version: number
  definition: NodeTemplateDefinition
  created_at: string
  updated_at: string
}

export interface NodeTemplateCreate {
  name: string
  display_name: string
  category: string
  scope: Scope
  definition: NodeTemplateDefinition
  change_note?: string
}

export interface MetaTemplateField {
  key: string
  label: string
  type:
    | 'string'
    | 'string_array'
    | 'json_schema'
    | 'code_block'
    | 'edge_list'
    | 'json'
    | 'bool'
    | 'number'
  required?: boolean
  hint?: string
  pattern?: string
  max_length?: number
}

export interface MetaTemplate {
  version: number
  fields: MetaTemplateField[]
}
