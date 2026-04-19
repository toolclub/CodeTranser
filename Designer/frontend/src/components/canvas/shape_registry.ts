/** X6 自定义 Shape 注册表。
 *
 *  复杂节点靠 HTML 渲染(比 SVG 灵活),每个节点由一个 Vue 组件/模板渲染:
 *  - 上半部标题栏:实例名 + 节点模板类别 + 运行状态
 *  - 中段:字段快照(EntrySize=4, Mask=null)
 *  - 下半部:按 `edge_semantics` 生成的端口列表
 *
 *  Bundle 是嵌入型容器(parent 节点),子节点实例 embeds 进去。
 */
import { Graph, Node } from '@antv/x6'

import type { EdgeSemantic, NodeTemplateCard } from '@/types'

export const NODE_SHAPE = 'cascade-node'
export const BUNDLE_SHAPE = 'cascade-bundle'

/** 已注册标志位,避免重复注册导致 X6 警告 */
let _registered = false

export interface NodeShapeData {
  /** 节点实例 id(= node.id) */
  instance_id: string
  template_id: string
  template_name: string
  category: string
  instance_name: string
  field_values: Record<string, unknown>
  edge_semantics: EdgeSemantic[]
  /** 调色盘(用于头部颜色) */
  color: string
}

/** 根据 category 返回颜色(与原型一致) */
export function colorOfCategory(cat: string): string {
  const map: Record<string, string> = {
    table_ops: '#6366f1',
    validation: '#10b981',
    branching: '#8b5cf6',
    action: '#f59e0b',
    merge: '#06b6d4',
    utility: '#64748b',
  }
  return map[cat] ?? '#6366f1'
}

export function registerShapes(): void {
  if (_registered) return
  _registered = true

  Graph.registerNode(
    NODE_SHAPE,
    {
      inherit: 'html',
      width: 220,
      height: 76,
      data: {} as NodeShapeData,
      // 端口由 ports.groups 定义;add/remove 由 PortRegistry 运行时处理
      ports: {
        groups: {
          in: { position: 'left', attrs: { circle: _portCircle('#64748b') } },
          // 每个 edge semantic 对应一个 out_<field> 组
        },
        items: [{ id: 'in-1', group: 'in' }],
      },
    },
    true,
  )

  Graph.registerNode(
    BUNDLE_SHAPE,
    {
      inherit: 'rect',
      width: 320,
      height: 200,
      zIndex: -1,
      attrs: {
        body: {
          fill: 'rgba(99,102,241,0.04)',
          stroke: '#6366f1',
          strokeDasharray: '4 4',
          rx: 10,
          ry: 10,
        },
        label: {
          text: '',
          refX: 12,
          refY: 8,
          textAnchor: 'start',
          textVerticalAnchor: 'top',
          fill: '#6366f1',
          fontWeight: 600,
          fontSize: 12,
        },
      },
    },
    true,
  )
}

function _portCircle(color: string) {
  return {
    r: 5,
    magnet: true,
    stroke: color,
    strokeWidth: 1.5,
    fill: '#fff',
  }
}

/** 根据 NodeTemplateCard 计算节点的初始 data + 端口配置。 */
export function buildNodeData(
  instanceId: string,
  instanceName: string,
  tpl: NodeTemplateCard,
  fieldValues: Record<string, unknown> = {},
): { data: NodeShapeData; portItems: Array<{ id: string; group: string }> } {
  const data: NodeShapeData = {
    instance_id: instanceId,
    template_id: tpl.id,
    template_name: tpl.name,
    category: tpl.category,
    instance_name: instanceName,
    field_values: fieldValues,
    edge_semantics: tpl.edge_semantics,
    color: colorOfCategory(tpl.category),
  }
  const portItems = [
    { id: 'in', group: 'in' },
    ...tpl.edge_semantics.map((e) => ({ id: `out:${e.field}`, group: `out:${e.field}` })),
  ]
  return { data, portItems }
}

/** 在 Graph 上为某个节点动态注册它需要的 out 端口 group(基于 edge_semantics)。 */
export function ensureOutGroups(node: Node, edgeSemantics: EdgeSemantic[]): void {
  const ports = node.getPorts()
  const existing = new Set(ports.map((p) => p.group))
  for (const es of edgeSemantics) {
    const g = `out:${es.field}`
    if (!existing.has(g)) {
      node.addPort({ id: g, group: g, attrs: { text: { text: es.field } } })
    }
  }
}
