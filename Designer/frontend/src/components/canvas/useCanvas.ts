/** X6 画布封装:Shape 注册 → Graph 实例 → forest ⇄ 渲染双向同步。
 *
 *  OO 定位:
 *  - 画布是 CanvasController(持有 X6 Graph);store 是 Single Source Of Truth(forest JSON)
 *  - renderSnapshot(forest) 把 JSON → X6 节点/边;onModelChange 把 X6 改动 → store mutation
 *  - 端口由 shape_registry.ensureOutGroups 按 edge_semantics 动态注册
 */
import { Edge, Graph, type Node } from '@antv/x6'

import { useGraphStore } from '@/stores/graph'
import { useTemplatesStore } from '@/stores/templates'
import type { ForestSnapshot, NodeTemplateCard } from '@/types'
import { newBundleId, newEdgeId, newInstanceId } from '@/utils/ids'

import {
  BUNDLE_SHAPE,
  NODE_SHAPE,
  buildNodeData,
  colorOfCategory,
  ensureOutGroups,
  registerShapes,
} from './shape_registry'

export interface UseCanvasHooks {
  onSelect?: (node: Node | null) => void
}

export interface CanvasController {
  graph: Graph
  renderSnapshot(f: ForestSnapshot): void
  createInstanceFromTemplate(templateId: string, pos: { x: number; y: number }): void
  createBundle(name?: string): void
  dispose(): void
}

export function useCanvas(container: HTMLDivElement, hooks: UseCanvasHooks = {}): CanvasController {
  registerShapes()

  const graph = new Graph({
    container,
    autoResize: true,
    background: { color: '#f6f7fb' },
    grid: { visible: true, type: 'dot', args: { color: '#d1d5db' } },
    panning: true,
    mousewheel: { enabled: true, modifiers: ['ctrl'] },
    embedding: {
      enabled: true,
      findParent: 'bbox',
      validate: ({ parent, child }) => parent?.shape === BUNDLE_SHAPE && child.shape === NODE_SHAPE,
    },
    connecting: {
      router: 'manhattan',
      connector: 'rounded',
      snap: { radius: 20 },
      allowBlank: false,
      allowLoop: false,
      allowNode: false,
      allowEdge: false,
      allowMulti: 'withPort',
      validateMagnet: ({ magnet }) => magnet?.getAttribute('magnet') === 'true',
      validateConnection: ({ sourcePort, targetPort }) =>
        Boolean(sourcePort?.startsWith('out:') && (targetPort === 'in' || targetPort?.startsWith('in'))),
    },
    highlighting: {
      magnetAdsorbed: {
        name: 'stroke',
        args: { attrs: { stroke: '#6366f1', strokeWidth: 2 } },
      },
    },
  })

  const store = useGraphStore()
  const templates = useTemplatesStore()

  let suppressEvents = false
  let lastForestRendered: string | null = null

  // --- 渲染: forest → Graph ---
  function renderSnapshot(f: ForestSnapshot) {
    const sig = JSON.stringify(f)
    if (sig === lastForestRendered) return
    lastForestRendered = sig

    suppressEvents = true
    try {
      graph.clearCells()
      // bundles 先建(zIndex 低,作为 embedding parent)
      const bundleMap = new Map<string, Node>()
      for (const b of f.bundles) {
        const node = graph.addNode({
          id: b.bundle_id,
          shape: BUNDLE_SHAPE,
          x: _hashPos(b.bundle_id).x,
          y: _hashPos(b.bundle_id).y,
          attrs: { label: { text: b.name } },
          data: { bundle_id: b.bundle_id, name: b.name, description: b.description ?? '' },
        })
        bundleMap.set(b.bundle_id, node)
      }
      // nodes
      for (const n of f.node_instances) {
        const card = _resolveCard(n)
        if (!card) continue
        const { data, portItems } = buildNodeData(
          n.instance_id,
          n.instance_name,
          card,
          n.field_values,
        )
        const pos = _hashPos(n.instance_id, 40)
        const node = graph.addNode({
          id: n.instance_id,
          shape: NODE_SHAPE,
          x: pos.x,
          y: pos.y,
          width: 220,
          height: 80,
          ports: { items: portItems },
          html: () => _renderHtml(data),
          data,
        })
        ensureOutGroups(node, card.edge_semantics)
        if (n.bundle_id && bundleMap.has(n.bundle_id)) {
          node.setParent(bundleMap.get(n.bundle_id)!)
        }
      }
      // edges
      for (const e of f.edges) {
        graph.addEdge({
          id: e.edge_id,
          shape: 'edge',
          source: { cell: e.from, port: `out:${e.edge_semantic}` },
          target: { cell: e.to, port: 'in' },
          labels: [
            {
              attrs: { text: { text: e.edge_semantic, fill: '#6366f1', fontSize: 11 } },
              position: { distance: 0.5 },
            },
          ],
          attrs: { line: { stroke: '#94a3b8', strokeWidth: 1.5 } },
          data: { edge_id: e.edge_id, semantic: e.edge_semantic },
        })
      }
    } finally {
      suppressEvents = false
    }
  }

  function _resolveCard(n: ForestSnapshot['node_instances'][number]): NodeTemplateCard | null {
    const byId = templates.byId.get(n.template_id)
    if (byId) return byId
    // fallback: 用 snapshot 构造假 card
    const snap = (n.template_snapshot ?? {}) as Record<string, unknown>
    const edgeSemRaw = snap.edge_semantics as Array<{ field: string; description?: string }> | undefined
    return {
      id: n.template_id,
      name: (snap.name as string) ?? 'Unknown',
      display_name: (snap.display_name as string) ?? 'Unknown',
      category: (snap.category as string) ?? 'utility',
      current_version: n.template_version,
      input_schema: (snap.input_schema as Record<string, unknown>) ?? {},
      edge_semantics: edgeSemRaw ?? [],
    }
  }

  function _renderHtml(data: ReturnType<typeof buildNodeData>['data']): HTMLElement {
    const el = document.createElement('div')
    el.className = 'x6-node'
    el.innerHTML = `
      <header style="background:${data.color}">
        <span>${data.template_name}</span>
        <span class="iid">${data.instance_id}</span>
      </header>
      <div class="body">
        <div class="name">${_escape(data.instance_name || data.instance_id)}</div>
      </div>
      <footer>${data.edge_semantics
        .map((s) => `<span class="sem">${s.field}</span>`)
        .join('')}</footer>
    `
    el.style.cssText = `
      width:100%;height:100%;background:#fff;border:1px solid #e5e7eb;border-radius:8px;
      overflow:hidden;display:flex;flex-direction:column;font-size:12px;
    `
    const style = el.ownerDocument.createElement('style')
    style.textContent = `
      .x6-node header { padding:4px 10px;color:#fff;display:flex;justify-content:space-between;font-weight:600;font-size:11px; }
      .x6-node header .iid { opacity:.7;font-size:10px; }
      .x6-node .body { padding:6px 10px;flex:1; }
      .x6-node .body .name { font-weight:600;font-size:13px;color:#0f172a; }
      .x6-node footer { border-top:1px dashed #e5e7eb;padding:4px 10px;display:flex;gap:6px;flex-wrap:wrap; }
      .x6-node footer .sem { font-size:10px;color:#64748b;padding:1px 6px;border-radius:3px;background:#eef0f7; }
    `
    el.appendChild(style)
    return el
  }

  // 简单哈希位置(稳定 + 分散);avoid 所有节点堆在原点
  function _hashPos(seed: string, offset = 0): { x: number; y: number } {
    let h = 0
    for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0
    return {
      x: 40 + ((h >>> 8) % 800) + offset,
      y: 40 + ((h >>> 16) % 500) + offset,
    }
  }

  // --- 反向同步: Graph → store ---
  graph.on('node:added', ({ node }: { node: Node }) => {
    if (suppressEvents) return
    // 节点已是在 renderSnapshot 里添加的,忽略
  })

  graph.on('node:removed', ({ node }: { node: Node }) => {
    if (suppressEvents) return
    if (node.shape === NODE_SHAPE) store.removeNodeInstance(node.id)
    if (node.shape === BUNDLE_SHAPE) store.removeBundle(node.id)
  })

  graph.on('edge:connected', ({ isNew, edge }: { isNew: boolean; edge: Edge }) => {
    if (suppressEvents || !isNew) return
    const src = edge.getSourceCellId()
    const dst = edge.getTargetCellId()
    const srcPort = edge.getSourcePortId() ?? ''
    if (!src || !dst) return
    const semantic = srcPort.startsWith('out:') ? srcPort.slice(4) : 'next'
    const edgeId = newEdgeId()
    edge.setProp('id', edgeId)
    store.addEdge({ edge_id: edgeId, from: src, to: dst, edge_semantic: semantic })
  })

  graph.on('node:embedded', ({ node, currentParent }: { node: Node; currentParent?: Node }) => {
    if (suppressEvents || node.shape !== NODE_SHAPE) return
    const bid = currentParent?.shape === BUNDLE_SHAPE ? currentParent.id : null
    store.setBundleMembership(node.id, bid)
  })

  graph.on('node:change:parent', ({ node, current }: { node: Node; current?: string | null }) => {
    if (suppressEvents || node.shape !== NODE_SHAPE) return
    const bid = current ?? null
    // 只处理 bundle 归属变化(避免 embedded 重复触发 store 更新)
    const inst = store.forest.node_instances.find((n) => n.instance_id === node.id)
    if (inst && inst.bundle_id !== bid) {
      store.setBundleMembership(node.id, bid)
    }
  })

  graph.on('node:click', ({ node }: { node: Node }) => hooks.onSelect?.(node))
  graph.on('blank:click', () => hooks.onSelect?.(null))

  function createInstanceFromTemplate(
    templateId: string,
    pos: { x: number; y: number },
  ): void {
    const tpl = templates.byId.get(templateId)
    if (!tpl) return
    const iid = newInstanceId()
    store.addNodeInstance({
      instance_id: iid,
      template_id: tpl.id,
      template_version: tpl.current_version,
      instance_name: `${tpl.name}_${iid.slice(2, 8)}`,
      field_values: {},
      bundle_id: null,
    })
  }

  function createBundle(name = '新 Bundle'): void {
    store.addBundle({
      bundle_id: newBundleId(),
      name,
      description: '',
      node_instance_ids: [],
    })
  }

  function dispose(): void {
    graph.dispose()
  }

  return { graph, renderSnapshot, createInstanceFromTemplate, createBundle, dispose }
}

function _escape(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string))
}
