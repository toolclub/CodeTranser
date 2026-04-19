<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { runsApi } from '@/api'
import { Card, Tag } from '@/components/ui'
import type { RunEvent, RunSummary } from '@/types'

const route = useRoute()
const runId = route.params.id as string

const run = ref<RunSummary | null>(null)
const events = ref<RunEvent[]>([])
let ws: WebSocket | null = null
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    run.value = await runsApi.detail(runId)
  } catch (e) {
    error.value = (e as Error).message
  }
  subscribe()
})

onBeforeUnmount(() => ws?.close())

function subscribe() {
  try {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    ws = new WebSocket(`${proto}://${location.host}/ws/runs/${runId}/events`)
    ws.onmessage = (ev) => {
      try {
        const e = JSON.parse(ev.data) as RunEvent
        events.value.push(e)
        if (events.value.length > 500) events.value = events.value.slice(-500)
      } catch {
        /* noop */
      }
    }
  } catch {
    /* Ch11 未实装 */
  }
}
</script>

<template>
  <div class="page">
    <header class="hdr">
      <h2>Run {{ runId }}</h2>
      <Tag v-if="run" :kind="run.final_verdict === 'valid' ? 'success' : 'danger'">
        {{ run.status }} / {{ run.final_verdict ?? '-' }}
      </Tag>
    </header>

    <div v-if="error" class="card"><div class="card-body" style="color: var(--danger)">{{ error }}</div></div>

    <Card title="阶段时间线">
      <div v-if="run">
        <p>graph_version_id = <span class="mono">{{ run.graph_version_id }}</span></p>
        <p>started_at: {{ run.started_at ?? '-' }}</p>
        <p>phase1: {{ run.phase1_verdict ?? '-' }}</p>
      </div>
    </Card>

    <Card title="实时事件(WebSocket)">
      <div class="ev-log">
        <div v-for="(e, i) in events" :key="i" class="ev-line">
          <span class="ts">{{ e.ts.slice(11, 19) }}</span>
          <span class="type">{{ e.type }}</span>
          <span v-if="e.phase" class="mono">P{{ e.phase }}</span>
          <span v-if="e.node_name" class="mono">{{ e.node_name }}</span>
          <span v-if="e.handler_name" class="mono">{{ e.handler_name }}</span>
          <span v-if="e.payload" class="muted mono">{{ JSON.stringify(e.payload) }}</span>
        </div>
        <div v-if="!events.length" class="dim">(暂无事件,WS 未连通或无事件)</div>
      </div>
    </Card>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 1200px; margin: 0 auto; }
.hdr { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.hdr h2 { margin: 0; font-size: 18px; }
.ev-log { max-height: 480px; overflow-y: auto; font-family: var(--mono); font-size: 11px; }
.ev-line { padding: 3px 6px; display: flex; gap: 8px; align-items: center; border-bottom: 1px solid var(--surface-3); }
.ev-line:hover { background: var(--surface-2); }
.ts { color: var(--text-dim); }
.type { color: var(--primary); font-weight: 600; }
</style>
