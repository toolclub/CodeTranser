<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { runsApi } from '@/api'
import { Card, Tag } from '@/components/ui'
import type { RunSummary } from '@/types'

const router = useRouter()
const list = ref<RunSummary[]>([])
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    list.value = await runsApi.list()
  } catch (e) {
    error.value = (e as Error).message
  }
})

function kindOfVerdict(v: string | null): 'success' | 'danger' | 'warning' | 'default' {
  if (v === 'valid') return 'success'
  if (v === 'invalid') return 'danger'
  if (v === 'inconclusive') return 'warning'
  return 'default'
}
</script>

<template>
  <div class="page">
    <header class="hdr"><h2>Run 列表</h2></header>
    <div v-if="error" class="card"><div class="card-body" style="color: var(--danger)">{{ error }}</div></div>
    <div v-else-if="!list.length" class="card"><div class="card-body">暂无运行记录。</div></div>
    <div v-else class="list">
      <Card v-for="r in list" :key="r.id">
        <div class="row" @click="router.push(`/runs/${r.id}`)">
          <span class="mono">{{ r.id }}</span>
          <Tag :kind="kindOfVerdict(r.final_verdict)">{{ r.final_verdict ?? '-' }}</Tag>
          <span class="muted mono" style="flex: 1">gv: {{ r.graph_version_id }}</span>
          <span class="dim">{{ r.created_at }}</span>
        </div>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 1100px; margin: 0 auto; }
.hdr h2 { margin: 0 0 16px; font-size: 18px; }
.list { display: flex; flex-direction: column; gap: 8px; }
.row { display: flex; gap: 12px; align-items: center; cursor: pointer; padding: 8px; border-radius: 4px; }
.row:hover { background: var(--surface-3); }
</style>
