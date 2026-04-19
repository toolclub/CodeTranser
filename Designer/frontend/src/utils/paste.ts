/** 前端版 `paste.rebuild_ids`,对应后端 `app/domain/graph/paste.py::rebuild_ids`。
 *  用于 Ctrl+C / Ctrl+V:把一个 {bundles, node_instances, edges} 片段全部换新 id,内部引用跟着改。
 */
import type { ForestSnapshot } from '@/types'
import { newHex } from './ids'

export function rebuildIds(fragment: Partial<ForestSnapshot>): ForestSnapshot {
  const idMap = new Map<string, string>()
  const renew = (oldId: string): string => {
    if (idMap.has(oldId)) return idMap.get(oldId)!
    const prefix = oldId.includes('_') ? oldId.split('_', 1)[0] : 'x'
    const newId = `${prefix}_${newHex(8)}`
    idMap.set(oldId, newId)
    return newId
  }

  const out: ForestSnapshot = {
    bundles: (fragment.bundles ?? []).map((b) => ({
      ...b,
      bundle_id: renew(b.bundle_id),
      node_instance_ids: b.node_instance_ids.map((x) => idMap.get(x) ?? x),
    })),
    node_instances: (fragment.node_instances ?? []).map((n) => ({
      ...n,
      instance_id: renew(n.instance_id),
    })),
    edges: (fragment.edges ?? []).map((e) => ({
      ...e,
      edge_id: renew(e.edge_id),
      from: idMap.get(e.from) ?? e.from,
      to: idMap.get(e.to) ?? e.to,
    })),
    metadata: fragment.metadata ?? {},
  }
  // 第二遍刷回 bundle 成员(因为节点 id 是在节点后才生成,上面改 bundle 时可能没 map 到)
  for (const b of out.bundles) {
    b.node_instance_ids = b.node_instance_ids.map((x) => idMap.get(x) ?? x)
  }
  return out
}
