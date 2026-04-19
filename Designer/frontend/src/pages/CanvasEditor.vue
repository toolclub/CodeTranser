<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import FieldValueEditor from '@/components/canvas/FieldValueEditor.vue'
import { useCanvas } from '@/components/canvas/useCanvas'
import { Button, Tag } from '@/components/ui'
import { useGraphStore } from '@/stores/graph'
import { useTemplatesStore } from '@/stores/templates'
import { debounce } from '@/utils/debounce'
import { rebuildIds } from '@/utils/paste'
import type { NodeTemplateCard } from '@/types'

const route = useRoute()
const graphStore = useGraphStore()
const templatesStore = useTemplatesStore()

const canvasEl = ref<HTMLDivElement | null>(null)
const selectedNodeId = ref<string | null>(null)
let canvas: ReturnType<typeof useCanvas> | null = null

const graphId = ref<string>((route.params.graphId as string) ?? '')

onMounted(async () => {
  await templatesStore.refresh().catch(() => {})
  if (!canvasEl.value) return
  canvas = useCanvas(canvasEl.value, {
    onSelect(node) {
      selectedNodeId.value = node && node.shape === 'cascade-node' ? node.id : null
    },
  })

  if (graphId.value) {
    await loadGraph()
  }

  watch(
    () => graphStore.forest,
    (f) => canvas?.renderSnapshot(f),
    { immediate: true },
  )

  const autoSave = debounce(async () => {
    if (!graphId.value || !graphStore.dirty) return
    try { await graphStore.saveDraft(graphId.value) } catch { /* noop */ }
  }, 800)
  watch(() => graphStore.forest, autoSave, { deep: false })

  window.addEventListener('keydown', onKey)
})

onBeforeUnmount(() => {
  canvas?.dispose()
  window.removeEventListener('keydown', onKey)
})

async function loadGraph() {
  try { await graphStore.loadGraph(graphId.value) } catch (e) { console.warn('loadGraph failed', e) }
}

function onKey(e: KeyboardEvent) {
  const target = e.target as HTMLElement
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return
  if (e.ctrlKey || e.metaKey) {
    if (e.key === 'z' && !e.shiftKey) { e.preventDefault(); graphStore.undo() }
    if ((e.key === 'z' && e.shiftKey) || e.key === 'y') { e.preventDefault(); graphStore.redo() }
    if (e.key === 'c' && selectedNodeId.value) copySelected()
    if (e.key === 'v') pasteClipboard()
  }
  if (e.key === 'Delete' || e.key === 'Backspace') {
    if (selectedNodeId.value) {
      graphStore.removeNodeInstance(selectedNodeId.value)
      selectedNodeId.value = null
      e.preventDefault()
    }
  }
}

function copySelected() {
  if (!selectedNodeId.value) return
  const n = graphStore.forest.node_instances.find((x) => x.instance_id === selectedNodeId.value)
  if (!n) return
  navigator.clipboard.writeText(JSON.stringify({ node_instances: [n], bundles: [], edges: [] })).catch(() => {})
}

async function pasteClipboard() {
  try {
    const text = await navigator.clipboard.readText()
    const frag = JSON.parse(text)
    if (!frag.node_instances) return
    const rebuilt = rebuildIds(frag)
    for (const n of rebuilt.node_instances) graphStore.addNodeInstance(n)
    for (const b of rebuilt.bundles) graphStore.addBundle(b)
    for (const e of rebuilt.edges) graphStore.addEdge(e)
  } catch { /* 非 JSON,忽略 */ }
}

function onDragStart(e: DragEvent, tpl: NodeTemplateCard) {
  e.dataTransfer?.setData('application/cascade-template', tpl.id)
}
function onCanvasDrop(e: DragEvent) {
  const tplId = e.dataTransfer?.getData('application/cascade-template')
  if (!tplId || !canvas) return
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  canvas.createInstanceFromTemplate(tplId, { x: e.clientX - rect.left, y: e.clientY - rect.top })
}
function onCanvasDragOver(e: DragEvent) {
  if (e.dataTransfer?.types.includes('application/cascade-template')) e.preventDefault()
}

const selectedInstance = computed(() => {
  if (!selectedNodeId.value) return null
  return graphStore.forest.node_instances.find((n) => n.instance_id === selectedNodeId.value) ?? null
})
const selectedTemplate = computed<NodeTemplateCard | null>(() => {
  const inst = selectedInstance.value
  if (!inst) return null
  return templatesStore.byId.get(inst.template_id) ?? null
})

function onFieldsChange(v: Record<string, unknown>) {
  if (!selectedInstance.value) return
  graphStore.updateNodeInstance(selectedInstance.value.instance_id, { field_values: v })
}

async function saveVersion() {
  if (!graphId.value) return
  const msg = prompt('提交说明:', '') ?? ''
  await graphStore.saveVersion(graphId.value, msg, graphStore.info?.latest_version_id ?? null)
}

async function validateNow() {
  try {
    const { graphsApi } = await import('@/api')
    const rep = await graphsApi.validate(graphStore.forest)
    alert(rep.ok ? '✓ 校验通过' + (rep.warnings.length ? ` (${rep.warnings.length} warnings)` : '')
                  : '✗ 校验失败:\n' + rep.errors.map((e) => e.message).join('\n'))
  } catch (e) {
    alert('校验失败: ' + (e as Error).message)
  }
}
</script>

<template>
  <div class="canvas-page">
    <aside class="left">
      <div class="panel-hd">节点库</div>
      <div class="tpl-list">
        <div
          v-for="tpl in templatesStore.cards"
          :key="tpl.id"
          class="tpl-item"
          draggable="true"
          @dragstart="(e) => onDragStart(e, tpl)"
        >
          <span class="ic">{{ tpl.name.slice(0, 2).toUpperCase() }}</span>
          <div class="meta">
            <div class="name">{{ tpl.name }}</div>
            <div class="desc">{{ tpl.display_name }}</div>
          </div>
          <Tag kind="outline">v{{ tpl.current_version }}</Tag>
        </div>
        <div v-if="!templatesStore.cards.length" class="empty">
          暂无节点模板(后端 API 未接入时为空)。
        </div>
      </div>
    </aside>

    <section class="center">
      <header class="tb">
        <Button size="sm" :disabled="!graphStore.canUndo" @click="graphStore.undo">撤销</Button>
        <Button size="sm" :disabled="!graphStore.canRedo" @click="graphStore.redo">重做</Button>
        <Button size="sm" @click="canvas?.createBundle()">新建 Bundle</Button>
        <span class="grow" />
        <Tag v-if="graphStore.dirty" kind="warning">有未保存改动</Tag>
        <Tag v-else kind="success">已保存</Tag>
        <Button variant="ghost" size="sm" @click="validateNow">校验</Button>
        <Button variant="primary" size="sm" :disabled="!graphId" @click="saveVersion">发布版本</Button>
      </header>
      <div ref="canvasEl" class="canvas-host" @drop="onCanvasDrop" @dragover="onCanvasDragOver" />
    </section>

    <aside class="right">
      <div class="panel-hd">属性</div>
      <div v-if="selectedInstance" class="props-body">
        <div class="kv"><span>instance_id</span><code>{{ selectedInstance.instance_id }}</code></div>
        <div class="kv"><span>template</span><code>{{ selectedInstance.template_id }} v{{ selectedInstance.template_version }}</code></div>
        <div class="kv"><span>bundle</span><code>{{ selectedInstance.bundle_id ?? '(orphan)' }}</code></div>
        <div class="form-row">
          <label>instance_name</label>
          <input
            class="input"
            :value="selectedInstance.instance_name"
            @input="(e) => graphStore.updateNodeInstance(selectedInstance!.instance_id, { instance_name: (e.target as HTMLInputElement).value })"
          />
        </div>
        <div class="divider" />
        <h4 class="sec">字段(由 input_schema 驱动)</h4>
        <FieldValueEditor
          v-if="selectedTemplate"
          :schema="selectedTemplate.input_schema"
          :modelValue="selectedInstance.field_values"
          @update:modelValue="onFieldsChange"
        />
        <div v-else class="empty">模板未加载。</div>
      </div>
      <div v-else class="empty">选择一个节点查看属性。</div>
    </aside>
  </div>
</template>

<style scoped>
.canvas-page {
  display: grid;
  grid-template-columns: 260px 1fr 320px;
  height: 100%;
  background: var(--surface-2);
}
.left, .right { background: #fff; border: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; }
.panel-hd { padding: 10px 14px; font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.4px; border-bottom: 1px solid var(--border); }
.tpl-list { overflow-y: auto; flex: 1; padding: 8px; display: flex; flex-direction: column; gap: 4px; }
.tpl-item { display: flex; gap: 10px; align-items: center; padding: 8px 10px; border-radius: 6px; cursor: grab; border: 1px solid transparent; transition: all .12s; }
.tpl-item:hover { background: var(--primary-soft); border-color: rgba(99,102,241,.2); }
.tpl-item .ic { width: 28px; height: 28px; border-radius: 6px; display: grid; place-items: center; color: #fff; font-weight: 600; font-size: 12px; background: var(--primary); }
.tpl-item .meta { flex: 1; min-width: 0; }
.tpl-item .name { font-size: 13px; font-weight: 500; color: var(--text); }
.tpl-item .desc { font-size: 11px; color: var(--text-muted); }
.empty { padding: 24px; text-align: center; color: var(--text-dim); font-size: 12px; }

.center { display: flex; flex-direction: column; min-width: 0; }
.tb { padding: 8px 12px; display: flex; gap: 8px; align-items: center; background: #fff; border-bottom: 1px solid var(--border); }
.canvas-host { flex: 1; min-height: 0; }

.props-body { overflow-y: auto; padding: 12px 14px; }
.kv { display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; color: var(--text-muted); gap: 12px; }
.kv code { background: var(--surface-3); padding: 1px 6px; border-radius: 3px; font-family: var(--mono); font-size: 11px; color: var(--text); word-break: break-all; text-align: right; }
.sec { margin: 8px 0 10px; font-size: 12px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
</style>
