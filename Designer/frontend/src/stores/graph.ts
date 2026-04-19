import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'

import { graphsApi } from '@/api'
import type {
  BundleDTO,
  EdgeDTO,
  ForestSnapshot,
  GraphInfo,
  NodeInstanceDTO,
} from '@/types'

/** 画布画面的 Forest 状态管理 + 撤销/重做。 */
const MAX_HISTORY = 50

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v)) as T
}

function emptyForest(): ForestSnapshot {
  return { bundles: [], node_instances: [], edges: [], metadata: {} }
}

export const useGraphStore = defineStore('graph', () => {
  const info = ref<GraphInfo | null>(null)
  // shallowRef 防止 X6 大对象触发深度响应
  const forest = shallowRef<ForestSnapshot>(emptyForest())
  const dirty = ref(false)

  const history: ForestSnapshot[] = []
  const future: ForestSnapshot[] = []

  const canUndo = computed(() => history.length > 0)
  const canRedo = computed(() => future.length > 0)

  function setForest(next: ForestSnapshot, markDirty = true) {
    history.push(clone(forest.value))
    if (history.length > MAX_HISTORY) history.shift()
    future.length = 0
    forest.value = next
    if (markDirty) dirty.value = true
  }

  function replaceForest(next: ForestSnapshot) {
    forest.value = next
    dirty.value = false
    history.length = 0
    future.length = 0
  }

  function undo() {
    const prev = history.pop()
    if (!prev) return
    future.unshift(clone(forest.value))
    forest.value = prev
  }

  function redo() {
    const nxt = future.shift()
    if (!nxt) return
    history.push(clone(forest.value))
    forest.value = nxt
  }

  function addNodeInstance(n: NodeInstanceDTO) {
    const next = clone(forest.value)
    next.node_instances.push(n)
    setForest(next)
  }

  function updateNodeInstance(iid: string, patch: Partial<NodeInstanceDTO>) {
    const next = clone(forest.value)
    const idx = next.node_instances.findIndex((n) => n.instance_id === iid)
    if (idx < 0) return
    next.node_instances[idx] = { ...next.node_instances[idx], ...patch }
    setForest(next)
  }

  function removeNodeInstance(iid: string) {
    const next = clone(forest.value)
    next.node_instances = next.node_instances.filter((n) => n.instance_id !== iid)
    next.edges = next.edges.filter((e) => e.from !== iid && e.to !== iid)
    for (const b of next.bundles) {
      b.node_instance_ids = b.node_instance_ids.filter((x) => x !== iid)
    }
    setForest(next)
  }

  function addEdge(e: EdgeDTO) {
    const next = clone(forest.value)
    next.edges.push(e)
    setForest(next)
  }

  function removeEdge(eid: string) {
    const next = clone(forest.value)
    next.edges = next.edges.filter((e) => e.edge_id !== eid)
    setForest(next)
  }

  function addBundle(b: BundleDTO) {
    const next = clone(forest.value)
    next.bundles.push(b)
    setForest(next)
  }

  function removeBundle(bid: string) {
    const next = clone(forest.value)
    // 成员降级为游离(不删节点)
    next.bundles = next.bundles.filter((b) => b.bundle_id !== bid)
    for (const n of next.node_instances) {
      if (n.bundle_id === bid) n.bundle_id = null
    }
    setForest(next)
  }

  function setBundleMembership(iid: string, bid: string | null) {
    const next = clone(forest.value)
    // 从所有 bundle 中移除
    for (const b of next.bundles) {
      b.node_instance_ids = b.node_instance_ids.filter((x) => x !== iid)
    }
    // 加入目标
    if (bid) {
      const target = next.bundles.find((b) => b.bundle_id === bid)
      if (target && !target.node_instance_ids.includes(iid)) {
        target.node_instance_ids.push(iid)
      }
    }
    const n = next.node_instances.find((x) => x.instance_id === iid)
    if (n) n.bundle_id = bid
    setForest(next)
  }

  async function loadGraph(graphId: string) {
    info.value = await graphsApi.detail(graphId)
    // 先拉 draft,再 fallback 到最新 version
    try {
      const draft = await graphsApi.getDraft(graphId)
      if (draft) return replaceForest(draft)
    } catch {
      /* noop */
    }
    const g = info.value
    if (g && g.latest_version_id) {
      const versions = await graphsApi.listVersions(graphId)
      if (versions.length) {
        const snap = await graphsApi.getVersion(graphId, versions[0].version_number)
        replaceForest(snap)
        return
      }
    }
    replaceForest(emptyForest())
  }

  async function saveDraft(graphId: string) {
    await graphsApi.saveDraft(graphId, forest.value)
    dirty.value = false
  }

  async function saveVersion(
    graphId: string,
    commitMessage = '',
    parentVersionId: string | null = null,
  ) {
    const r = await graphsApi.saveVersion(graphId, {
      snapshot: forest.value,
      commit_message: commitMessage,
      parent_version_id: parentVersionId,
    })
    dirty.value = false
    return r
  }

  return {
    info,
    forest,
    dirty,
    canUndo,
    canRedo,
    setForest,
    replaceForest,
    undo,
    redo,
    addNodeInstance,
    updateNodeInstance,
    removeNodeInstance,
    addEdge,
    removeEdge,
    addBundle,
    removeBundle,
    setBundleMembership,
    loadGraph,
    saveDraft,
    saveVersion,
  }
})
