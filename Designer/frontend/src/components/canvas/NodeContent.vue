<script setup lang="ts">
import { computed } from 'vue'

import type { NodeShapeData } from './shape_registry'

const props = defineProps<{ data: NodeShapeData; selected?: boolean }>()

const fieldsPreview = computed(() => {
  const entries = Object.entries(props.data.field_values ?? {})
  return entries.slice(0, 3).map(([k, v]) => `${k}=${_short(v)}`).join('  ')
})

function _short(v: unknown): string {
  if (v === null) return 'null'
  const s = typeof v === 'object' ? JSON.stringify(v) : String(v)
  return s.length > 20 ? s.slice(0, 20) + '…' : s
}
</script>

<template>
  <div class="x6-node" :class="{ selected }">
    <header :style="{ background: data.color }">
      <span class="tpl">{{ data.template_name }}</span>
      <span class="iid mono">{{ data.instance_id }}</span>
    </header>
    <div class="body">
      <div class="name">{{ data.instance_name || data.instance_id }}</div>
      <div v-if="fieldsPreview" class="fields mono">{{ fieldsPreview }}</div>
    </div>
    <footer v-if="data.edge_semantics.length">
      <span v-for="es in data.edge_semantics" :key="es.field" class="semantic">{{ es.field }}</span>
    </footer>
  </div>
</template>

<style scoped>
.x6-node {
  width: 100%;
  height: 100%;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: border-color 0.12s, box-shadow 0.12s;
}
.x6-node.selected {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--primary-soft);
}
.x6-node header {
  padding: 4px 10px;
  color: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
}
.x6-node header .iid {
  opacity: 0.7;
  font-size: 10px;
}
.x6-node .body {
  padding: 6px 10px;
  flex: 1;
  min-height: 30px;
}
.x6-node .body .name {
  font-weight: 600;
  font-size: 13px;
  color: var(--text);
}
.x6-node .body .fields {
  color: var(--text-muted);
  font-size: 11px;
  margin-top: 3px;
}
.x6-node footer {
  border-top: 1px dashed var(--border);
  padding: 4px 10px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.x6-node footer .semantic {
  font-size: 10px;
  color: var(--text-muted);
  font-family: var(--mono);
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--surface-3);
}
</style>
