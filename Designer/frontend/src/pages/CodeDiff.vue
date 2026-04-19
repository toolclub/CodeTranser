<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { runsApi } from '@/api'
import { Card } from '@/components/ui'

const route = useRoute()
const runId = route.params.runId as string
const data = ref<{ files: Record<string, { before: string; after: string }> } | null>(null)
const error = ref<string | null>(null)
const selected = ref<string | null>(null)

onMounted(async () => {
  try {
    data.value = await runsApi.getCodeDiff(runId)
    selected.value = Object.keys(data.value.files)[0] ?? null
  } catch (e) {
    error.value = (e as Error).message
  }
})

const selectedDiff = computed(() =>
  selected.value && data.value ? data.value.files[selected.value] : null,
)

function renderDiff(before: string, after: string): Array<{ k: '-' | '+' | ' '; text: string }> {
  const bl = before.split('\n')
  const al = after.split('\n')
  const out: Array<{ k: '-' | '+' | ' '; text: string }> = []
  let i = 0
  let j = 0
  while (i < bl.length || j < al.length) {
    if (bl[i] === al[j]) {
      out.push({ k: ' ', text: bl[i] ?? '' })
      i++; j++
    } else if (i < bl.length && !al.includes(bl[i])) {
      out.push({ k: '-', text: bl[i] }); i++
    } else {
      out.push({ k: '+', text: al[j] ?? '' }); j++
    }
  }
  return out
}
</script>

<template>
  <div class="page">
    <header class="hdr">
      <h2>代码 Diff · Run {{ runId }}</h2>
    </header>
    <div v-if="error" class="card"><div class="card-body" style="color: var(--danger)">{{ error }}</div></div>
    <div v-else-if="data" class="grid">
      <Card title="文件">
        <div v-for="name in Object.keys(data.files)" :key="name" class="file-item" :class="{ active: name === selected }" @click="selected = name">
          <span class="mono">{{ name }}</span>
        </div>
      </Card>
      <Card v-if="selectedDiff" :title="selected ?? '选择文件'">
        <pre class="code"><span
          v-for="(line, i) in renderDiff(selectedDiff.before, selectedDiff.after)"
          :key="i"
          :class="line.k === '+' ? 'plus' : line.k === '-' ? 'minus' : 'same'"
        >{{ line.k }} {{ line.text }}
</span></pre>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 1400px; margin: 0 auto; }
.hdr h2 { margin: 0 0 16px; font-size: 18px; }
.grid { display: grid; grid-template-columns: 240px 1fr; gap: 12px; }
.file-item { padding: 6px 10px; cursor: pointer; border-radius: 4px; }
.file-item:hover { background: var(--surface-2); }
.file-item.active { background: var(--primary-soft); color: var(--primary); }
.code span.plus { color: var(--success); background: rgba(16, 185, 129, 0.1); display: block; }
.code span.minus { color: var(--danger); background: rgba(239, 68, 68, 0.1); display: block; }
.code span.same { color: var(--text-dim); display: block; }
</style>
